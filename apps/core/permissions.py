"""RBAC permissions for NEC4 roles.

The App is used by Contractor staff only.
PM and Supervisor are external companies (not system users).
All create/edit actions require contractor or admin role.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to one or more NEC4 roles."""

    allowed_roles: list[str] = []

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class ContractorRequiredMixin(RoleRequiredMixin):
    """Contractor staff and administrators."""
    allowed_roles = ['contractor', 'admin']


# Aliases kept for backward compatibility — both resolve to contractor+admin
class PMRequiredMixin(ContractorRequiredMixin):
    """Alias: project-level create/edit — contractor or admin."""
    pass


class PMOrContractorRequiredMixin(ContractorRequiredMixin):
    """Alias: same as ContractorRequiredMixin."""
    pass


class SupervisorRequiredMixin(ContractorRequiredMixin):
    """Alias: same as ContractorRequiredMixin."""
    pass


class AnyRoleRequiredMixin(LoginRequiredMixin):
    """Any authenticated user may access."""
    pass


class PlanLimitMixin(LoginRequiredMixin):
    """
    Blocks a create view when the user's organisation has hit its plan limit.

    Subclasses must set `limit_check` to one of: 'project' | 'member'
    """
    limit_check: str = 'project'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(request.user)

        if org is None:
            # No organisation yet — allow superusers, block everyone else
            if request.user.is_superuser:
                return super().dispatch(request, *args, **kwargs)
            messages.error(request, 'You must belong to an organisation to create resources.')
            return redirect('core:dashboard')

        if self.limit_check == 'project' and not org.can_add_project():
            plan = org.plan
            messages.error(
                request,
                f'Your {plan.name} plan allows a maximum of {plan.max_projects} '
                f'project{"s" if plan.max_projects != 1 else ""}. '
                'Please upgrade your plan to create more projects.'
            )
            return redirect('subscriptions:billing')

        if self.limit_check == 'member' and not org.can_add_member():
            plan = org.plan
            messages.error(
                request,
                f'Your {plan.name} plan allows a maximum of {plan.max_members} '
                f'member{"s" if plan.max_members != 1 else ""}. '
                'Please upgrade your plan to add more members.'
            )
            return redirect('subscriptions:billing')

        return super().dispatch(request, *args, **kwargs)


class PlanLimitMixin(LoginRequiredMixin):
    """
    Blocks a create view when the user's organisation has hit its plan limit.

    Subclasses must set `limit_check` to one of: 'project' | 'member'
    """
    limit_check: str = 'project'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        from apps.subscriptions.utils import get_user_organisation
        org = get_user_organisation(request.user)

        if org is None:
            # No organisation yet — allow superusers, block everyone else
            if request.user.is_superuser:
                return super().dispatch(request, *args, **kwargs)
            messages.error(request, 'You must belong to an organisation to create resources.')
            return redirect('core:dashboard')

        if self.limit_check == 'project' and not org.can_add_project():
            plan = org.plan
            messages.error(
                request,
                f'Your {plan.name} plan allows a maximum of {plan.max_projects} '
                f'project{"s" if plan.max_projects != 1 else ""}. '
                'Please upgrade your plan to create more projects.'
            )
            return redirect('subscriptions:billing')

        if self.limit_check == 'member' and not org.can_add_member():
            plan = org.plan
            messages.error(
                request,
                f'Your {plan.name} plan allows a maximum of {plan.max_members} '
                f'member{"s" if plan.max_members != 1 else ""}. '
                'Please upgrade your plan to add more members.'
            )
            return redirect('subscriptions:billing')

        return super().dispatch(request, *args, **kwargs)
