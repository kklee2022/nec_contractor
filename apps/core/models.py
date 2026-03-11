"""Core models: Custom User, UserProfile, and base mixins."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with NEC4 roles."""

    class Role(models.TextChoices):
        CONTRACTOR = 'contractor', _('Contractor')
        PROJECT_MANAGER = 'pm', _('Project Manager')
        SUPERVISOR = 'supervisor', _('Supervisor')
        ADMIN = 'admin', _('Administrator')

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CONTRACTOR,
    )
    organisation = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        full = self.get_full_name()
        return full if full else self.username

    # --- Role helpers ---
    @property
    def is_contractor(self):
        return self.role == self.Role.CONTRACTOR

    @property
    def is_project_manager(self):
        return self.role == self.Role.PROJECT_MANAGER

    @property
    def is_supervisor(self):
        return self.role == self.Role.SUPERVISOR

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_pm(self):
        return self.role == self.Role.PROJECT_MANAGER


class TimeStampedModel(models.Model):
    """Abstract base: adds created_at / updated_at to every model."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).active()


class SoftDeleteModel(models.Model):
    """Abstract base: soft-delete instead of hard-delete."""

    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def hard_delete(self):
        super().delete()
