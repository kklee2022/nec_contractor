"""Subscription & Organisation management views."""

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import timezone

from .models import Organisation, OrganisationMembership, SubscriptionPlan
from .forms import MemberInviteForm, MemberRoleForm
from .utils import get_user_organisation, require_org_admin, require_org_owner


# ─── Helpers ───────────────────────────────────────────────────────────────────

def _get_membership(user):
    """Return the user's active membership, or None."""
    return OrganisationMembership.objects.filter(
        user=user, is_active=True
    ).select_related('organisation', 'organisation__plan').first()


# ─── Organisation dashboard ─────────────────────────────────────────────────

@login_required
def org_dashboard(request):
    membership = _get_membership(request.user)
    if not membership:
        messages.info(request, 'You are not part of any organisation yet.')
        return redirect('core:dashboard')
    org = membership.organisation
    members = org.memberships.filter(is_active=True).select_related('user').order_by('user__last_name')
    context = {
        'org': org,
        'membership': membership,
        'members': members,
        'plan': org.plan,
    }
    return render(request, 'subscriptions/org_dashboard.html', context)


# ─── Member management ──────────────────────────────────────────────────────

@login_required
def member_list(request):
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'You do not have permission to manage members.')
        return redirect('subscriptions:org_dashboard')
    org = membership.organisation
    members = org.memberships.select_related('user').order_by('org_role', 'user__last_name')
    context = {'org': org, 'members': members, 'membership': membership}
    return render(request, 'subscriptions/member_list.html', context)


@login_required
def member_invite(request):
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'You do not have permission to invite members.')
        return redirect('subscriptions:org_dashboard')
    org = membership.organisation

    # Check plan limit
    if not org.can_add_member():
        messages.error(
            request,
            f'Your {org.plan_name} plan allows a maximum of {org.plan.max_members} members. '
            'Please upgrade to add more.'
        )
        return redirect('subscriptions:member_list')

    form = MemberInviteForm(request.POST or None)
    if form.is_valid():
        user = form.get_user()
        nec_role = form.cleaned_data['nec_role']
        org_role = form.cleaned_data['org_role']

        # Check if already a member
        existing = OrganisationMembership.objects.filter(organisation=org, user=user).first()
        if existing:
            if existing.is_active:
                messages.warning(request, f'{user.get_full_name() or user.email} is already a member.')
            else:
                existing.is_active = True
                existing.org_role = org_role
                existing.save()
                user.role = nec_role
                user.save(update_fields=['role'])
                messages.success(request, f'{user.get_full_name() or user.email} has been re-activated.')
        else:
            OrganisationMembership.objects.create(organisation=org, user=user, org_role=org_role)
            user.role = nec_role
            user.save(update_fields=['role'])
            messages.success(request, f'{user.get_full_name() or user.email} has been added to {org.name}.')
        return redirect('subscriptions:member_list')

    context = {'form': form, 'org': org}
    return render(request, 'subscriptions/member_invite.html', context)


@login_required
def member_role_change(request, pk):
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'Access denied.')
        return redirect('subscriptions:org_dashboard')
    target = get_object_or_404(OrganisationMembership, pk=pk, organisation=membership.organisation)
    if target.is_owner and not membership.is_owner:
        messages.error(request, 'Only the owner can reassign the owner role.')
        return redirect('subscriptions:member_list')

    form = MemberRoleForm(request.POST or None, instance=target)
    if form.is_valid():
        form.save()
        messages.success(request, 'Role updated.')
        return redirect('subscriptions:member_list')

    context = {'form': form, 'target': target, 'org': membership.organisation}
    return render(request, 'subscriptions/member_role_form.html', context)


@login_required
def member_remove(request, pk):
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'Access denied.')
        return redirect('subscriptions:org_dashboard')
    target = get_object_or_404(OrganisationMembership, pk=pk, organisation=membership.organisation)
    if target.is_owner:
        messages.error(request, 'Cannot remove the organisation owner.')
        return redirect('subscriptions:member_list')
    if request.method == 'POST':
        target.is_active = False
        target.save()
        messages.success(request, f'{target.user.get_full_name() or target.user.username} has been removed.')
        return redirect('subscriptions:member_list')
    context = {'target': target, 'org': membership.organisation}
    return render(request, 'subscriptions/member_confirm_remove.html', context)


# ─── Billing ────────────────────────────────────────────────────────────────

@login_required
def billing(request):
    membership = _get_membership(request.user)
    if not membership:
        return redirect('core:dashboard')
    org = membership.organisation
    plans = SubscriptionPlan.objects.all()
    context = {
        'org': org,
        'plans': plans,
        'membership': membership,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'subscriptions/billing.html', context)


@login_required
def billing_success(request):
    messages.success(request, 'Subscription updated successfully! Your plan is now active.')
    return redirect('subscriptions:billing')


@login_required
def create_checkout_session(request):
    """Create a Stripe Checkout session for plan upgrade."""
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'Only organisation admins can manage billing.')
        return redirect('subscriptions:billing')

    plan_tier = request.POST.get('plan_tier')
    plan = get_object_or_404(SubscriptionPlan, tier=plan_tier)

    if not plan.stripe_price_id:
        messages.error(request, 'This plan is not yet available for purchase. Please contact support.')
        return redirect('subscriptions:billing')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    org = membership.organisation

    try:
        # Get or create Stripe customer
        if org.stripe_customer_id:
            customer_id = org.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=org.name,
                metadata={'org_id': str(org.pk)},
            )
            org.stripe_customer_id = customer.id
            org.save(update_fields=['stripe_customer_id'])
            customer_id = customer.id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
            mode='subscription',
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={'org_id': str(org.pk), 'plan_tier': plan_tier},
        )
        return redirect(session.url, permanent=False)
    except stripe.StripeError as e:
        messages.error(request, f'Payment error: {e.user_message}')
        return redirect('subscriptions:billing')


@login_required
def billing_portal(request):
    """Redirect to Stripe Customer Portal for subscription management."""
    membership = _get_membership(request.user)
    if not membership or not membership.is_org_admin:
        messages.error(request, 'Access denied.')
        return redirect('subscriptions:billing')

    org = membership.organisation
    if not org.stripe_customer_id:
        messages.error(request, 'No billing account found. Please subscribe first.')
        return redirect('subscriptions:billing')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        portal = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=settings.STRIPE_CANCEL_URL,
        )
        return redirect(portal.url, permanent=False)
    except stripe.StripeError as e:
        messages.error(request, f'Could not open billing portal: {e.user_message}')
        return redirect('subscriptions:billing')


# ─── Stripe Webhook ─────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        _handle_checkout_complete(session)

    elif event['type'] in ('customer.subscription.updated', 'customer.subscription.deleted'):
        subscription = event['data']['object']
        _handle_subscription_update(subscription)

    return HttpResponse(status=200)


def _handle_checkout_complete(session):
    """Activate the plan after a successful checkout."""
    org_id = session.get('metadata', {}).get('org_id')
    plan_tier = session.get('metadata', {}).get('plan_tier')
    if not org_id or not plan_tier:
        return
    try:
        org = Organisation.objects.get(pk=org_id)
        plan = SubscriptionPlan.objects.get(tier=plan_tier)
        org.plan = plan
        org.stripe_subscription_id = session.get('subscription', '')
        org.status = Organisation.Status.ACTIVE
        org.save(update_fields=['plan', 'stripe_subscription_id', 'status'])
    except (Organisation.DoesNotExist, SubscriptionPlan.DoesNotExist):
        pass


def _handle_subscription_update(subscription):
    """Sync subscription status from Stripe."""
    customer_id = subscription.get('customer')
    if not customer_id:
        return
    try:
        org = Organisation.objects.get(stripe_customer_id=customer_id)
        status = subscription.get('status')
        period_end = subscription.get('current_period_end')
        if status == 'active':
            org.status = Organisation.Status.ACTIVE
        elif status in ('canceled', 'unpaid'):
            org.status = Organisation.Status.CANCELLED
        if period_end:
            org.subscription_current_period_end = timezone.datetime.fromtimestamp(
                period_end, tz=timezone.utc
            )
        org.save(update_fields=['status', 'subscription_current_period_end'])
    except Organisation.DoesNotExist:
        pass
