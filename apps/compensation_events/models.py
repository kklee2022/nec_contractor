"""Compensation Event models with FSM — NEC4 Clauses 60–66."""

from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_fsm import FSMField, transition
from auditlog.registry import auditlog
from apps.core.models import TimeStampedModel


class CompensationEvent(TimeStampedModel):
    """
    A Compensation Event under NEC4 ECC Clauses 60–66.

    State machine:
        notified → quoted → pm_reviewing → implemented
                         ↘ rejected
        notified → assumed (if PM fails to reply in 8 weeks — Clause 61.4)
    """

    class Clause(models.TextChoices):
        CL60_1_1 = '60.1(1)', _('60.1(1) — PM instruction to change Works Info')
        CL60_1_2 = '60.1(2)', _('60.1(2) — PM does not reply to communication')
        CL60_1_3 = '60.1(3)', _('60.1(3) — PM instruction to stop or not start work')
        CL60_1_4 = '60.1(4)', _('60.1(4) — PM instruction to change Key Date')
        CL60_1_5 = '60.1(5)', _('60.1(5) — PM or Supervisor failure')
        CL60_1_6 = '60.1(6)', _('60.1(6) — PM does not accept work')
        CL60_1_7 = '60.1(7)', _('60.1(7) — Uncollected object')
        CL60_1_8 = '60.1(8)', _('60.1(8) — Physical conditions')
        CL60_1_9 = '60.1(9)', _('60.1(9) — Adverse weather')
        CL60_1_10 = '60.1(10)', _('60.1(10) — Employer risk event')
        CL60_1_11 = '60.1(11)', _('60.1(11) — Test or inspection causes delay')
        CL60_1_12 = '60.1(12)', _('60.1(12) — Employer does not provide')
        CL60_1_13 = '60.1(13)', _('60.1(13) — Breach by Employer')
        CL60_1_14 = '60.1(14)', _('60.1(14) — Preventive measures')
        CL60_1_OTHER = 'other', _('Other')

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='compensation_events',
    )
    reference = models.CharField(max_length=50, blank=True)
    clause = models.CharField(max_length=20, choices=Clause.choices, default=Clause.CL60_1_1)
    description = models.TextField(help_text='Description of the compensation event')
    notified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='notified_ces',
    )
    notification_date = models.DateTimeField(default=timezone.now)

    # FSM state
    state = FSMField(default='notified', protected=True)

    # PM reply tracking
    pm_instruction_date = models.DateTimeField(null=True, blank=True)
    pm_reply = models.TextField(blank=True)
    pm_accepted = models.BooleanField(null=True, blank=True)

    # Quotation
    quotation_submitted_date = models.DateTimeField(null=True, blank=True)
    quotation_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    quotation_time_extension = models.IntegerField(
        null=True, blank=True,
        help_text='Time extension in days'
    )
    quotation_detail = models.TextField(blank=True)

    # Implementation
    implemented_date = models.DateTimeField(null=True, blank=True)
    implemented_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    implemented_time_extension = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-notification_date']
        verbose_name = 'Compensation Event'
        verbose_name_plural = 'Compensation Events'

    def __str__(self):
        return f'{self.reference or "CE"} — {self.project.reference} [{self.state}]'

    def save(self, *args, **kwargs):
        if not self.reference:
            count = CompensationEvent.objects.filter(project=self.project).count() + 1
            self.reference = f'CE-{count:04d}'
        super().save(*args, **kwargs)

    # --- Deadline helpers ---
    @property
    def pm_reply_deadline(self):
        """PM must respond within 8 weeks of notification (Clause 61.4)."""
        return self.notification_date + timedelta(weeks=8)

    @property
    def pm_reply_overdue(self):
        return timezone.now() > self.pm_reply_deadline and self.state == 'notified'

    @property
    def quotation_deadline(self):
        """Contractor must submit quotation within 3 weeks of PM instruction."""
        if self.pm_instruction_date:
            return self.pm_instruction_date + timedelta(weeks=3)
        return None

    @property
    def quotation_overdue(self):
        if self.quotation_deadline:
            return timezone.now() > self.quotation_deadline and self.state == 'notified'
        return False

    # --- FSM Transitions ---
    @transition(field=state, source='notified', target='quoted')
    def submit_quotation(self, cost, time_extension, detail, submitted_by=None):
        """Contractor submits quotation (Clause 62)."""
        self.quotation_submitted_date = timezone.now()
        self.quotation_cost = cost
        self.quotation_time_extension = time_extension
        self.quotation_detail = detail

    @transition(field=state, source='notified', target='assumed',
                conditions=[lambda self: self.pm_reply_overdue])
    def assume_ce(self):
        """Quotation deemed accepted if PM fails to respond in 8 weeks (Clause 61.4)."""
        pass

    @transition(field=state, source='quoted', target='pm_reviewing')
    def pm_start_review(self):
        """PM begins reviewing quotation."""
        pass

    @transition(field=state, source=['quoted', 'pm_reviewing', 'assumed'], target='implemented')
    def implement(self, cost=None, time_extension=None):
        """CE is accepted and implemented (Clause 65)."""
        self.implemented_date = timezone.now()
        if cost is not None:
            self.implemented_cost = cost
        if time_extension is not None:
            self.implemented_time_extension = time_extension

    @transition(field=state, source=['quoted', 'pm_reviewing'], target='rejected')
    def reject(self, reason=''):
        """PM rejects the CE."""
        self.pm_reply = reason

    @transition(field=state, source='rejected', target='notified')
    def resubmit(self):
        """Contractor resubmits after rejection."""
        pass


class CEAttachment(TimeStampedModel):
    """Supporting document for a Compensation Event."""

    ce = models.ForeignKey(CompensationEvent, on_delete=models.CASCADE, related_name='attachments')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='compensation_events/attachments/')
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'Attachment for {self.ce.reference}'


auditlog.register(CompensationEvent)
