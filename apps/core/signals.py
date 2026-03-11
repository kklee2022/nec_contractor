"""Signals for core app."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    """Hook for post-user-creation tasks (e.g. onboarding email)."""
    if created:
        pass  # future: send welcome email
