"""Early Warnings app configuration."""

from django.apps import AppConfig


class EarlyWarningsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.early_warnings'
    label = 'early_warnings'
