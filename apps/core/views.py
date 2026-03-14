from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.urls import reverse
from .forms import (
    UserRegistrationForm, UserProfileForm, PersonForm,
    ContractorForm, ProjectManagerForm, SupervisorForm,
    ContractorOrganisationForm,
)
from .models import User, ContractorOrganisation


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
    """List Contractor staff (admin only)."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied. Admin role required.')
        return redirect('core:dashboard')

    search = request.GET.get('q', '')
    users = User.objects.filter(role=User.Role.CONTRACTOR)

    if search:
        users = users.filter(
            first_name__icontains=search
        ) | users.filter(
            last_name__icontains=search
        ) | users.filter(
            email__icontains=search
        )

    context = {
        'people': users.order_by('last_name', 'first_name'),
        'search': search,
        'total': User.objects.filter(role=User.Role.CONTRACTOR).count(),
        'active_count': User.objects.filter(role=User.Role.CONTRACTOR, is_active=True).count(),
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

    back_url = reverse('core:people_list')
    return render(request, 'core/person_confirm_deactivate.html', {'person': person, 'back_url': back_url})


# ---------------------------------------------------------------------------
# Role-specific CRUD helpers
# ---------------------------------------------------------------------------

ROLE_SLUG_MAP = {
    'contractors': User.Role.CONTRACTOR,
}

ROLE_CONFIG = {
    User.Role.CONTRACTOR: {
        'label': 'Contractor Staff', 'plural': 'Contractor Staff',
        'slug': 'contractors', 'icon': 'bi-person-hard-hat', 'color': 'primary',
    },
}

ROLE_FORMS = {
    User.Role.CONTRACTOR: ContractorForm,
}


def _get_role_or_404(role_slug):
    role = ROLE_SLUG_MAP.get(role_slug)
    if not role:
        raise Http404(f'Unknown role slug: {role_slug}')
    return role, ROLE_CONFIG[role], ROLE_FORMS[role]


@login_required
def role_person_list(request, role_slug):
    """List people for one specific role (contractors / project-managers / supervisors)."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    role, config, _ = _get_role_or_404(role_slug)
    qs = User.objects.filter(role=role)

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search) |
            Q(email__icontains=search) | Q(organisation__icontains=search)
        )

    context = {
        'people': qs.order_by('last_name', 'first_name'),
        'search': search,
        'config': config,
        'role_slug': role_slug,
        'total': User.objects.filter(role=role).count(),
        'active_count': User.objects.filter(role=role, is_active=True).count(),
    }
    if request.htmx:
        return render(request, 'core/_role_person_table.html', context)
    return render(request, 'core/role_person_list.html', context)


@login_required
def role_person_create(request, role_slug):
    """Create a new person for a specific role."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    role, config, FormClass = _get_role_or_404(role_slug)

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, f'{config["label"]} created successfully.')
            return redirect('core:role_person_list', role_slug=role_slug)
    else:
        form = FormClass()

    context = {
        'form': form,
        'config': config,
        'role_slug': role_slug,
        'is_new': True,
        'page_title': f'Add {config["label"]}',
        'list_url': reverse('core:role_person_list', kwargs={'role_slug': role_slug}),
    }
    return render(request, 'core/role_person_form.html', context)


@login_required
def role_person_edit(request, role_slug, pk):
    """Edit an existing person for a specific role."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    role, config, FormClass = _get_role_or_404(role_slug)
    person = get_object_or_404(User, pk=pk, role=role)

    if request.method == 'POST':
        form = FormClass(request.POST, instance=person)
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, f'{config["label"]} updated successfully.')
            return redirect('core:role_person_list', role_slug=role_slug)
    else:
        form = FormClass(instance=person)

    context = {
        'form': form,
        'config': config,
        'role_slug': role_slug,
        'person': person,
        'is_new': False,
        'page_title': f'Edit {config["label"]}',
        'list_url': reverse('core:role_person_list', kwargs={'role_slug': role_slug}),
    }
    return render(request, 'core/role_person_form.html', context)


@login_required
def role_person_deactivate(request, role_slug, pk):
    """Toggle active/inactive for a role-specific person."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')

    role, config, _ = _get_role_or_404(role_slug)
    person = get_object_or_404(User, pk=pk, role=role)

    if person == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('core:role_person_list', role_slug=role_slug)

    if request.method == 'POST':
        person.is_active = not person.is_active
        person.save(update_fields=['is_active'])
        action = 'activated' if person.is_active else 'deactivated'
        if request.htmx:
            return render(request, 'core/_role_person_row.html', {
                'person': person,
                'config': config,
                'role_slug': role_slug,
            })
        messages.success(request, f'{person.get_full_name() or person.username} has been {action}.')
        return redirect('core:role_person_list', role_slug=role_slug)

    back_url = reverse('core:role_person_list', kwargs={'role_slug': role_slug})
    return render(request, 'core/person_confirm_deactivate.html', {
        'person': person,
        'back_url': back_url,
        'config': config,
    })


# ---------------------------------------------------------------------------
# Contractor Organisation CRUD (singleton company entity)
# ---------------------------------------------------------------------------

@login_required
def contractor_org_detail(request):
    """View the single Contractor Organisation (create redirect if none)."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')
    org = ContractorOrganisation.objects.first()
    if not org:
        return redirect('core:contractor_org_create')
    staff = org.staff.order_by('last_name', 'first_name')
    return render(request, 'core/contractor_org_detail.html', {
        'org': org,
        'staff': staff,
    })


@login_required
def contractor_org_create(request):
    """Create the Contractor Organisation."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')
    if ContractorOrganisation.objects.exists():
        messages.info(request, 'A Contractor company already exists.')
        return redirect('core:contractor_org_detail')
    form = ContractorOrganisationForm(request.POST or None)
    if form.is_valid():
        org = form.save()
        messages.success(request, f'Contractor company "{org.name}" created.')
        return redirect('core:contractor_org_detail')
    return render(request, 'core/contractor_org_form.html', {
        'form': form,
        'is_new': True,
        'page_title': 'Add Contractor Company',
    })


@login_required
def contractor_org_edit(request):
    """Edit the Contractor Organisation."""
    if not request.user.is_admin_user:
        messages.error(request, 'Access denied.')
        return redirect('core:dashboard')
    org = get_object_or_404(ContractorOrganisation, pk=ContractorOrganisation.objects.first().pk)
    form = ContractorOrganisationForm(request.POST or None, instance=org)
    if form.is_valid():
        form.save()
        messages.success(request, 'Contractor company details updated.')
        return redirect('core:contractor_org_detail')
    return render(request, 'core/contractor_org_form.html', {
        'form': form,
        'org': org,
        'is_new': False,
        'page_title': 'Edit Contractor Company',
    })
