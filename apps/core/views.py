from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .forms import UserRegistrationForm, UserProfileForm, PersonForm
from .models import User


class NECLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True


# ─── Registration ─────────────────────────────────────────────────────────────

def register_view(request):
    """Public registration — creates User + Organisation + Free plan membership."""
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    form = UserRegistrationForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.role = User.Role.ADMIN  # org owner gets admin role
            user.save()

            # Create organisation and assign Free plan
            from apps.subscriptions.models import Organisation, OrganisationMembership, SubscriptionPlan
            org_name = form.cleaned_data.get('organisation_name') or user.get_full_name() or user.username
            org = Organisation.objects.create(name=org_name)
            try:
                free_plan = SubscriptionPlan.objects.get(tier=SubscriptionPlan.Tier.FREE)
                org.plan = free_plan
                org.save(update_fields=['plan'])
            except SubscriptionPlan.DoesNotExist:
                pass

            OrganisationMembership.objects.create(
                organisation=org,
                user=user,
                org_role=OrganisationMembership.Role.OWNER,
            )

        from django.contrib.auth import login
        login(request, user)
        messages.success(
            request,
            f'Welcome to NEC4 ECC Platform, {user.first_name or user.username}! '
            'Your account and organisation have been created on the Free plan.'
        )
        return redirect('core:dashboard')

    return render(request, 'registration/register.html', {'form': form})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('core:profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'core/profile.html', {'form': form})


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    from apps.projects.models import Project
    from apps.early_warnings.models import EarlyWarning
    from apps.compensation_events.models import CompensationEvent
    from apps.subscriptions.utils import get_user_membership

    user = request.user
    membership = get_user_membership(user)

    # Scope data to user's organisation if possible, else fall back to member access
    if membership:
        projects = Project.objects.filter(
            organisation=membership.organisation
        ).select_related()[:5]
        recent_ews = EarlyWarning.objects.filter(
            project__organisation=membership.organisation
        ).select_related('project', 'raised_by').order_by('-created_at')[:5]
        open_ces = CompensationEvent.objects.filter(
            project__organisation=membership.organisation
        ).exclude(state='implemented').exclude(state='rejected').select_related('project')[:5]
    else:
        projects = Project.objects.filter(members=user).select_related()[:5]
        recent_ews = EarlyWarning.objects.filter(
            project__members=user
        ).select_related('project', 'raised_by').order_by('-created_at')[:5]
        open_ces = CompensationEvent.objects.filter(
            project__members=user
        ).exclude(state='implemented').exclude(state='rejected').select_related('project')[:5]

    context = {
        'projects': projects,
        'recent_ews': recent_ews,
        'open_ces': open_ces,
        'membership': membership,
        'org': membership.organisation if membership else None,
    }
    return render(request, 'core/dashboard.html', context)


# ─── People CRUD ──────────────────────────────────────────────────────────────

@login_required
def people_list_view(request):
    """List all Contractor, PM and Supervisor users (admin only)."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('core:dashboard')

    role_filter = request.GET.get('role', '')
    search = request.GET.get('q', '')
    users = User.objects.exclude(role=User.Role.ADMIN).exclude(is_superuser=True)

    if role_filter:
        users = users.filter(role=role_filter)
    if search:
        users = users.filter(
            first_name__icontains=search
        ) | users.filter(
            last_name__icontains=search
        ) | users.filter(
            email__icontains=search
        )

    context = {
        'people': users.order_by('role', 'last_name', 'first_name'),
        'role_filter': role_filter,
        'search': search,
        'roles': [(r.value, r.label) for r in User.Role if r != User.Role.ADMIN],
        'role_counts': {
            'contractor': User.objects.filter(role=User.Role.CONTRACTOR).count(),
            'pm': User.objects.filter(role=User.Role.PROJECT_MANAGER).count(),
            'supervisor': User.objects.filter(role=User.Role.SUPERVISOR).count(),
        },
    }
    return render(request, 'core/people_list.html', context)


@login_required
def person_create_view(request):
    """Create a new Contractor, PM, or Supervisor."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    form = PersonForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        messages.success(
            request,
            f'{user.get_full_name() or user.username} ({user.get_role_display()}) '
            'has been created successfully.'
        )
        return redirect('core:people_list')

    context = {'form': form, 'title': 'Add New Person', 'is_new': True}
    return render(request, 'core/person_form.html', context)


@login_required
def person_edit_view(request, pk):
    """Edit an existing user's details."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    person = get_object_or_404(User, pk=pk)
    form = PersonForm(request.POST or None, instance=person)
    if form.is_valid():
        form.save()
        messages.success(request, f'{person.get_full_name() or person.username} has been updated.')
        return redirect('core:people_list')

    context = {
        'form': form,
        'person': person,
        'title': f'Edit — {person.get_full_name() or person.username}',
        'is_new': False,
    }
    return render(request, 'core/person_form.html', context)


@login_required
def person_deactivate_view(request, pk):
    """Toggle active/inactive status of a user."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    person = get_object_or_404(User, pk=pk)
    if person == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('core:people_list')

    if request.method == 'POST':
        person.is_active = not person.is_active
        person.save(update_fields=['is_active'])
        action = 'activated' if person.is_active else 'deactivated'
        messages.success(request, f'{person.get_full_name() or person.username} has been {action}.')
        return redirect('core:people_list')

    return render(request, 'core/person_confirm_deactivate.html', {'person': person})
