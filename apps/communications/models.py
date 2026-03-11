"""Communications log — NEC4 Clause 13 (separate notifications)."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from auditlog.registry import auditlog
from apps.core.models import TimeStampedModel


class Communication(TimeStampedModel):
    """
    A formal contract communication under NEC4 Clause 13.
    Clause 13.7 requires each notice to be communicated separately.
    """

    class CommType(models.TextChoices):
        CE_NOTIFICATION = 'ce_notification', _('CE Notification (Cl.61.3)')
        EARLY_WARNING = 'early_warning', _('Early Warning (Cl.15)')
        PM_INSTRUCTION = 'pm_instruction', _('PM Instruction (Cl.14)')
        PROGRAMME_SUBMISSION = 'programme_submission', _('Programme Submission (Cl.31)')
        PROGRAMME_ACCEPTANCE = 'programme_acceptance', _('Programme Acceptance (Cl.31)')
        PAYMENT_NOTICE = 'payment_notice', _('Payment Notice (Cl.51)')
        GENERAL = 'general', _('General Communication')

    class Direction(models.TextChoices):
        PM_TO_CONTRACTOR = 'pm_to_contractor', _('PM → Contractor')
        CONTRACTOR_TO_PM = 'contractor_to_pm', _('Contractor → PM')
        CONTRACTOR_TO_SUPERVISOR = 'contractor_to_supervisor', _('Contractor → Supervisor')
        SUPERVISOR_TO_CONTRACTOR = 'supervisor_to_contractor', _('Supervisor → Contractor')

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='communications',
    )
    reference = models.CharField(max_length=50, blank=True)
    communication_type = models.CharField(max_length=30, choices=CommType.choices)
    direction = models.CharField(max_length=40, choices=Direction.choices)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_communications',
    )
    sent_date = models.DateTimeField(default=timezone.now)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_communications',
    )
    acknowledged_date = models.DateTimeField(null=True, blank=True)

    # Optional links to related objects
    linked_ce = models.ForeignKey(
        'compensation_events.CompensationEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='communications',
    )
    linked_ew = models.ForeignKey(
        'early_warnings.EarlyWarning',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='communications',
    )

    attachment = models.FileField(upload_to='communications/attachments/', blank=True, null=True)

    class Meta:
        ordering = ['-sent_date']
        verbose_name = 'Communication'
        verbose_name_plural = 'Communications Log'

    def __str__(self):
        return f'{self.reference or "COMM"} — {self.subject}'

    def save(self, *args, **kwargs):
        if not self.reference:
            count = Communication.objects.filter(project=self.project).count() + 1
            self.reference = f'COMM-{count:04d}'
        super().save(*args, **kwargs)

    def clean(self):
        """
        Enforce NEC4 Clause 13.7: each notice must be a separate communication.
        CE notifications and early warnings cannot be bundled on the same day.
        """
        SEPARATE_TYPES = ['ce_notification', 'early_warning']
        if self.communication_type in SEPARATE_TYPES:
            existing = Communication.objects.filter(
                project=self.project,
                sent_date__date=self.sent_date.date() if self.sent_date else timezone.now().date(),
                communication_type=self.communication_type,
            )
            if self.pk:
                existing = existing.exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    f'Clause 13.7: A {self.get_communication_type_display()} has already been '
                    f'issued today. Each notice must be communicated separately.'
                )


auditlog.register(Communication)
