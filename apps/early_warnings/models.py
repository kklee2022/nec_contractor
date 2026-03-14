"""Early Warning Register models — NEC4 Clause 15."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from apps.core.models import TimeStampedModel


class EarlyWarning(TimeStampedModel):
    """
    An Early Warning notice under NEC4 Clause 15.
    Either the PM or Contractor may raise an EW.
    """

    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        UNDER_REVIEW = 'under_review', _('Under Review')
        ACTIONED = 'actioned', _('Actioned')
        CLOSED = 'closed', _('Closed')

    class RaisedBy(models.TextChoices):
        CONTRACTOR = 'contractor', _('Contractor')
        PROJECT_MANAGER = 'pm', _('Project Manager')

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='early_warnings',
    )
    reference = models.CharField(max_length=50, blank=True, help_text='Auto-generated EW reference')
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='raised_early_warnings',
    )
    raised_by_party = models.CharField(max_length=20, choices=RaisedBy.choices)
    description = models.TextField(help_text='Describe the matter that could affect cost, time, or quality')
    potential_impact = models.TextField(help_text='Potential impact on the project')
    mitigation = models.TextField(blank=True, help_text='Proposed mitigation actions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    # Risk reduction meeting
    risk_reduction_meeting_date = models.DateField(null=True, blank=True)
    risk_reduction_meeting_notes = models.TextField(blank=True)

    resolved_date = models.DateField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_early_warnings',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Early Warning'
        verbose_name_plural = 'Early Warning Register'

    def __str__(self):
        return f'{self.reference or "EW"} — {self.project.reference}'

    def save(self, *args, **kwargs):
        # Auto-generate reference using project prefix
        if not self.reference:
            prefix = getattr(self.project, 'ew_reference_prefix', 'CNEW-') or 'CNEW-'
            count = EarlyWarning.objects.filter(project=self.project).count() + 1
            self.reference = f'{prefix}{count:04d}'
        super().save(*args, **kwargs)


class EarlyWarningAttachment(TimeStampedModel):
    """Supporting document for an Early Warning."""

    early_warning = models.ForeignKey(EarlyWarning, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='early_warnings/attachments/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'Attachment for {self.early_warning.reference}'


auditlog.register(EarlyWarning)
