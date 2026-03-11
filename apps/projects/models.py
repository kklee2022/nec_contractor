"""Project and Site models."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Project(TimeStampedModel):
    """An NEC4 ECC contract project."""

    class Status(models.TextChoices):
        TENDER = 'tender', _('Tender')
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        SUSPENDED = 'suspended', _('Suspended')

    name = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, unique=True, help_text='Contract reference number')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Key parties
    contractor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contracted_projects',
        limit_choices_to={'role': 'contractor'},
    )
    project_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='managed_projects',
        limit_choices_to={'role': 'pm'},
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervised_projects',
        limit_choices_to={'role': 'supervisor'},
    )

    # All users with access
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='projects',
        blank=True,
    )

    # Owning organisation (tenant)
    organisation = models.ForeignKey(
        'subscriptions.Organisation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='projects',
    )

    # Key dates
    start_date = models.DateField()
    completion_date = models.DateField()
    actual_completion = models.DateField(null=True, blank=True)

    # Financial
    contract_sum = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f'{self.reference} — {self.name}'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def days_remaining(self):
        from django.utils import timezone
        if self.completion_date:
            delta = self.completion_date - timezone.now().date()
            return delta.days
        return None


class Site(TimeStampedModel):
    """A physical site/section within a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sites')
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.project.reference} / {self.name}'


class Programme(TimeStampedModel):
    """Contract programme submission (Clause 31/32)."""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', _('Submitted')
        ACCEPTED = 'accepted', _('Accepted')
        NOT_ACCEPTED = 'not_accepted', _('Not Accepted')
        REVISED = 'revised', _('Revised')

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='programmes')
    revision = models.PositiveIntegerField(default=1)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='submitted_programmes',
    )
    submitted_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    pm_response = models.TextField(blank=True)
    programme_file = models.FileField(upload_to='programmes/', blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-revision']
        unique_together = ['project', 'revision']

    def __str__(self):
        return f'{self.project.reference} — Programme Rev {self.revision}'
