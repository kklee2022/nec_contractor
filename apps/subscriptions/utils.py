"""Helper utilities for the subscriptions app."""

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from .models import OrganisationMembership


def get_user_organisation(user):
    """Return the Organisation for the user's active membership, or None."""
    membership = OrganisationMembership.objects.filter(
        user=user, is_active=True
    ).select_related('organisation', 'organisation__plan').first()
    return membership.organisation if membership else None


def get_user_membership(user):
    """Return the user's active OrganisationMembership, or None."""
    return OrganisationMembership.objects.filter(
        user=user, is_active=True
    ).select_related('organisation', 'organisation__plan').first()


def require_org_admin(view_func):
    """Decorator: requires user to be an org admin or owner."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        membership = get_user_membership(request.user)
        if not membership or not membership.is_org_admin:
            messages.error(request, 'You must be an organisation admin to access this page.')
            return redirect('subscriptions:org_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_org_owner(view_func):
    """Decorator: requires user to be the org owner."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        membership = get_user_membership(request.user)
        if not membership or not membership.is_owner:
            messages.error(request, 'Only the organisation owner can perform this action.')
            return redirect('subscriptions:org_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped
