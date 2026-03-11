"""RBAC permissions for NEC4 roles."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restrict a view to one or more NEC4 roles."""

    allowed_roles: list[str] = []

    def test_func(self):
        return self.request.user.role in self.allowed_roles


class ContractorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['contractor', 'admin']


class PMRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['pm', 'admin']


class SupervisorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['supervisor', 'admin']


class PMOrContractorRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['pm', 'contractor', 'admin']


class AnyRoleRequiredMixin(LoginRequiredMixin):
    """Any authenticated user with a valid NEC4 role may access."""
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
