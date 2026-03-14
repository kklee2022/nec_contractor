"""Project and Site models."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel


class Project(TimeStampedModel):
    """An NEC4 ECC contract project (singleton — one per platform instance)."""

    class Status(models.TextChoices):
        TENDER = 'tender', _('Tender')
        ACTIVE = 'active', _('Active')
        COMPLETED = 'completed', _('Completed')
        SUSPENDED = 'suspended', _('Suspended')

    name = models.CharField(max_length=255)
    reference = models.CharField(max_length=100, unique=True, help_text='Contract reference number')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # ── Contract Parties ──────────────────────────────────────────────
    # The Contractor = the company (NEC4 Clause 11.2(6))
    contractor = models.ForeignKey(
        'core.ContractorOrganisation',
        on_delete=models.PROTECT,
        related_name='projects',
        verbose_name='Contractor',
        null=True,
        blank=True,
    )
    # Contractor's Representative = the individual (system user, role='contractor')
    contractor_representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='represented_projects',
        limit_choices_to={'role': 'contractor'},
        verbose_name="Contractor's Representative",
    )
    # The Project Manager = external company (NEC4 Clause 14.2)
    pm_company = models.CharField(
        max_length=255, blank=True,
        verbose_name='Project Manager Company',
        help_text='NEC4 Cl.14.2 — The company appointed as Project Manager.',
    )
    pm_representative = models.CharField(
        max_length=255, blank=True,
        verbose_name="PM's Named Representative",
    )
    pm_contact_email = models.EmailField(blank=True, verbose_name='PM Contact Email')
    # The Supervisor = external company (NEC4 Clause 14.4)
    supervisor_company = models.CharField(
        max_length=255, blank=True,
        verbose_name='Supervisor Company',
        help_text='NEC4 Cl.14.4 — The company appointed as Supervisor.',
    )
    supervisor_representative = models.CharField(
        max_length=255, blank=True,
        verbose_name="Supervisor's Named Representative",
    )
    supervisor_contact_email = models.EmailField(blank=True, verbose_name='Supervisor Contact Email')

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

    # Reference number prefixes
    ce_reference_prefix = models.CharField(
        max_length=20,
        default='CNCE-',
        verbose_name='CE Reference Prefix',
        help_text='Prefix for auto-generated Compensation Event reference numbers (e.g. CNCE-).',
    )
    ew_reference_prefix = models.CharField(
        max_length=20,
        default='CNEW-',
        verbose_name='EW Reference Prefix',
        help_text='Prefix for auto-generated Early Warning reference numbers (e.g. CNEW-).',
    )

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


# ─── Contract Data ─────────────────────────────────────────────────────────────

class ContractData(TimeStampedModel):
    """
    NEC Contract Data Part 1 — Employer's Data.
    One record per project (OneToOne).  Covers all standard sections:
    1-General, 3-Time, 4-Testing & Defects, 5-Payment, 8-Insurance,
    and Secondary Options X5/X7/X13/X14/X16/X20/Z.
    """

    class MainOption(models.TextChoices):
        A = 'A', _('A — Priced contract with activity schedule')
        B = 'B', _('B — Priced contract with bill of quantities')
        C = 'C', _('C — Target contract with activity schedule')
        D = 'D', _('D — Target contract with bill of quantities')
        E = 'E', _('E — Cost reimbursable contract')
        F = 'F', _('F — Management contract')

    project = models.OneToOneField(
        'Project', on_delete=models.CASCADE, related_name='contract_data',
    )

    # ── 1. General ────────────────────────────────────────────────────────
    nec_version = models.CharField(
        max_length=50, blank=True, default='NEC4 ECC Hong Kong Edition (July 2023)',
        verbose_name='NEC Version',
        help_text='e.g. NEC4 ECC Hong Kong Edition (July 2023), NEC3 ECC (April 2013)',
    )
    main_option = models.CharField(
        max_length=1, choices=MainOption.choices, blank=True,
        verbose_name='Main Option',
    )

    # Secondary Options — each as a boolean checkbox
    opt_x1  = models.BooleanField(default=False, verbose_name='X1 – Price adjustment for inflation')
    opt_x2  = models.BooleanField(default=False, verbose_name='X2 – Changes in the law')
    opt_x3  = models.BooleanField(default=False, verbose_name='X3 – Multiple currencies')
    opt_x4  = models.BooleanField(default=False, verbose_name='X4 – Parent company guarantee')
    opt_x5  = models.BooleanField(default=False, verbose_name='X5 – Sectional completion')
    opt_x6  = models.BooleanField(default=False, verbose_name='X6 – Bonus for early completion')
    opt_x7  = models.BooleanField(default=False, verbose_name='X7 – Delay damages')
    opt_x8  = models.BooleanField(default=False, verbose_name='X8 – Undertakings to the Client / Others')
    opt_x9  = models.BooleanField(default=False, verbose_name='X9 – Transfer of rights')
    opt_x10 = models.BooleanField(default=False, verbose_name='X10 – Information modelling')
    opt_x11 = models.BooleanField(default=False, verbose_name='X11 – Termination by the Client')
    opt_x12 = models.BooleanField(default=False, verbose_name='X12 – Multiparty collaboration')
    opt_x13 = models.BooleanField(default=False, verbose_name='X13 – Performance bond')
    opt_x14 = models.BooleanField(default=False, verbose_name='X14 – Advanced payment to the Contractor')
    opt_x15 = models.BooleanField(default=False, verbose_name="X15 – Limitation of Contractor's liability for design")
    opt_x16 = models.BooleanField(default=False, verbose_name='X16 – Retention')
    opt_x17 = models.BooleanField(default=False, verbose_name='X17 – Low performance damages')
    opt_x18 = models.BooleanField(default=False, verbose_name='X18 – Limitation of liability')
    opt_x20 = models.BooleanField(default=False, verbose_name='X20 – Key Performance Indicators')
    opt_x21 = models.BooleanField(default=False, verbose_name='X21 – Whole life cost')
    opt_x22 = models.BooleanField(default=False, verbose_name='X22 – Early Contractor Involvement')
    opt_w1  = models.BooleanField(default=False, verbose_name='W1 – Dispute resolution (adjudication / arbitration — HK applicable)')
    opt_w2  = models.BooleanField(default=False, verbose_name='W2 – Dispute resolution (UK HGCRA only — not applicable in HK)')
    opt_w3  = models.BooleanField(default=False, verbose_name='W3 – Dispute Avoidance Board')
    opt_z   = models.BooleanField(default=False, verbose_name='Z – Additional conditions of contract')

    works_description     = models.TextField(blank=True, verbose_name='Description of the Works')
    employer_name         = models.CharField(
        max_length=255, blank=True, verbose_name='The Client',
        help_text='NEC4 term. Referred to as "the Employer" in NEC3.',
    )
    site_information_ref  = models.CharField(max_length=255, blank=True, verbose_name='Site Information')
    adjudicator      = models.TextField(blank=True, verbose_name='Adjudicator')

    # ── 3. Time ───────────────────────────────────────────────────────────
    contract_date               = models.DateField(null=True, blank=True, verbose_name='Contract Date')
    starting_date               = models.DateField(null=True, blank=True, verbose_name='Starting Date')
    starting_date_notes         = models.CharField(
        max_length=255, blank=True, verbose_name='Starting Date Notes',
        help_text='e.g. "within 2 weeks from the Contract Date as notified by the PM"',
    )
    period_for_reply            = models.CharField(
        max_length=100, blank=True, verbose_name='Period for Reply',
        help_text='e.g. "3 weeks" or "6 weeks for events requiring Employer NOI"',
    )
    first_programme_weeks       = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='First Programme Submission (weeks after Contract Date)',
    )
    programme_revision_interval = models.CharField(
        max_length=100, blank=True, verbose_name='Programme Revision Interval',
        help_text='e.g. "1 month"',
    )
    completion_date             = models.DateField(null=True, blank=True, verbose_name='Completion Date')
    completion_description      = models.CharField(
        max_length=255, blank=True, verbose_name='Completion Date Description',
        help_text='e.g. "1,977 days after the starting date"',
    )
    risk_register_items         = models.TextField(
        blank=True, verbose_name='Risk Register Items',
        help_text='Enter each item on a new line.',
    )

    # ── 4. Testing & Defects ──────────────────────────────────────────────
    defects_date             = models.CharField(
        max_length=255, blank=True, verbose_name='Defects Date',
        help_text='e.g. "365 days after Completion of the whole of the works"',
    )
    defect_correction_period = models.CharField(
        max_length=255, blank=True, verbose_name='Defect Correction Period',
        help_text='e.g. "12 weeks"',
    )

    # ── 5. Payment ────────────────────────────────────────────────────────
    currency            = models.CharField(max_length=50, blank=True, default='HKD', verbose_name='Currency')
    assessment_interval = models.CharField(
        max_length=100, blank=True, verbose_name='Assessment Interval',
        help_text='e.g. "1 month"',
    )
    interest_rate       = models.TextField(
        blank=True, verbose_name='Interest Rate',
        help_text='e.g. "Bank of England base rate + 2% p.a."',
    )

    # ── 8. Risks & Insurance ──────────────────────────────────────────────
    min_indemnity_amount  = models.CharField(
        max_length=255, blank=True,
        verbose_name='Minimum Indemnity Limit',
        help_text='Minimum limit per event for property damage / bodily injury.',
    )
    insurance_notes       = models.TextField(
        blank=True, verbose_name='Professional Indemnity / Insurance Notes',
    )
    method_of_measurement = models.TextField(
        blank=True, verbose_name='Method of Measurement',
    )

    # ── X13 Performance Bond ─────────────────────────────────────────────
    performance_bond_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Performance Bond (%)',
    )

    # ── X14 Advance Payment ───────────────────────────────────────────────
    advance_payment_amount    = models.TextField(
        blank=True, verbose_name='Advance Payment Amount',
        help_text='Amount or formula, e.g. "lesser of 2% of tendered Prices or HKD500,000"',
    )
    advance_payment_repayment = models.TextField(
        blank=True, verbose_name='Advance Payment Repayment Terms',
        help_text='e.g. "monthly instalments of 1/6 starting at 7th month"',
    )

    # ── X16 Retention ─────────────────────────────────────────────────────
    retention_free_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Retention Free Amount',
    )
    retention_percentage  = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        verbose_name='Retention Percentage (%)',
    )
    retention_limit       = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Limit of Retention Amount',
    )

    # ── X20 Key Performance Indicators ────────────────────────────────────
    kpi_report_interval = models.CharField(
        max_length=100, blank=True, verbose_name='KPI Report Interval',
        help_text='e.g. "1 month"',
    )

    # ── Z Additional Conditions ───────────────────────────────────────────
    additional_conditions_ref   = models.CharField(
        max_length=255, blank=True, verbose_name='Additional Conditions Reference',
    )
    additional_conditions_notes = models.TextField(
        blank=True, verbose_name='Additional Conditions Notes',
    )

    class Meta:
        verbose_name = 'Contract Data'
        verbose_name_plural = 'Contract Data'

    def __str__(self):
        return f'Contract Data — {self.project}'

    @property
    def active_secondary_options(self):
        """Return list of (code, label) for every selected secondary option."""
        result = []
        for field in self._meta.get_fields():
            if hasattr(field, 'name') and field.name.startswith('opt_') and getattr(self, field.name):
                result.append(str(field.verbose_name))
        return result


class SiteAccessDate(models.Model):
    """
    Access Dates table (Contract Data Part 1, §3 Time).
    One row per site portion / working area.
    """
    contract_data      = models.ForeignKey(
        ContractData, on_delete=models.CASCADE, related_name='access_dates',
    )
    site_portion       = models.CharField(max_length=255, verbose_name='Part of Site / Portion')
    access_date        = models.DateField(null=True, blank=True, verbose_name='Access Date')
    access_description = models.CharField(
        max_length=255, blank=True, verbose_name='Access Date Description',
        help_text='e.g. "starting date" or "Not more than 90 days after the starting date"',
    )
    conditions         = models.CharField(
        max_length=255, blank=True, verbose_name='Conditions / Qualifications',
        help_text='e.g. subject to a specific clause reference',
    )

    class Meta:
        ordering = ['id']
        verbose_name = 'Site Access Date'
        verbose_name_plural = 'Site Access Dates'

    def __str__(self):
        return self.site_portion


class ContractSection(models.Model):
    """
    X5 / X7 Sections — one row per section.
    Records sectional completion date and associated delay damages.
    """
    contract_data         = models.ForeignKey(
        ContractData, on_delete=models.CASCADE, related_name='sections',
    )
    section_number        = models.PositiveSmallIntegerField(verbose_name='Section No.')
    description           = models.CharField(max_length=255, blank=True, verbose_name='Description')
    completion_days       = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Completion (days after starting date)',
    )
    completion_date       = models.DateField(
        null=True, blank=True, verbose_name='Completion Date (if known)',
    )
    delay_damages_per_day = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Delay Damages per Day',
    )
    delay_damages_formula = models.TextField(
        blank=True, verbose_name='Delay Damages Formula / Notes',
        help_text='Use for formula-based or variable delay damages.',
    )
    min_delay_damages     = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        verbose_name='Minimum Delay Damages per Day',
    )

    class Meta:
        ordering = ['section_number']
        unique_together = ['contract_data', 'section_number']
        verbose_name = 'Contract Section'
        verbose_name_plural = 'Contract Sections'

    def __str__(self):
        return f'Section {self.section_number}'

