"""Financial models — Defined Cost, Payment Applications, Invoices."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class DefinedCost(TimeStampedModel):
    """
    A Defined Cost entry for a project (NEC4 Clause 11.2(23)).
    Tracks actual costs incurred by the Contractor.
    """

    class CostCategory(models.TextChoices):
        PEOPLE = 'people', _('People')
        PLANT_EQUIPMENT = 'plant', _('Plant & Equipment')
        MATERIALS = 'materials', _('Materials')
        SUBCONTRACTOR = 'subcontractor', _('Subcontractor')
        CHARGES = 'charges', _('Charges')
        MANUFACTURE = 'manufacture', _('Manufacture & Fabrication')

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='defined_costs',
    )
    category = models.CharField(max_length=20, choices=CostCategory.choices)
    description = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default='GBP')
    cost_date = models.DateField()
    receipt = models.FileField(upload_to='financial/receipts/', blank=True, null=True)
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='entered_costs',
    )
    linked_ce = models.ForeignKey(
        'compensation_events.CompensationEvent',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='defined_costs',
    )

    class Meta:
        ordering = ['-cost_date']
        verbose_name = 'Defined Cost'
        verbose_name_plural = 'Defined Costs'

    def __str__(self):
        return f'{self.project.reference} | {self.category} | HKD{self.amount}'


class PaymentApplication(TimeStampedModel):
    """
    A payment application submitted by the Contractor (NEC4 Clause 50).
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        SUBMITTED = 'submitted', _('Submitted')
        PM_ASSESSED = 'pm_assessed', _('PM Assessed')
        PAID = 'paid', _('Paid')
        DISPUTED = 'disputed', _('Disputed')

    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='payment_applications',
    )
    application_number = models.PositiveIntegerField()
    period_from = models.DateField()
    period_to = models.DateField()
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_applications',
    )
    submitted_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # Amounts
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    retention = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    previous_certificates = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # PM assessment
    pm_assessed_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    pm_assessment_date = models.DateField(null=True, blank=True)
    pm_notes = models.TextField(blank=True)

    # Payment
    payment_date = models.DateField(null=True, blank=True)
    payment_certificate = models.FileField(upload_to='financial/certificates/', blank=True, null=True)

    class Meta:
        ordering = ['-application_number']
        unique_together = ['project', 'application_number']
        verbose_name = 'Payment Application'
        verbose_name_plural = 'Payment Applications'

    def __str__(self):
        return f'{self.project.reference} — Application #{self.application_number}'

    @property
    def is_overdue(self):
        """PM must certify within 7 days of application (NEC4 Clause 51.1)."""
        from django.utils import timezone
        if self.status == 'submitted' and self.submitted_date:
            return timezone.now() > self.submitted_date + timezone.timedelta(days=7)
        return False
