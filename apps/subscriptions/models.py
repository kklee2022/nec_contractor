"""Subscription, Organisation, and Membership models for multi-tenancy."""

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class SubscriptionPlan(TimeStampedModel):
    """Defines the available subscription tiers and their limits."""

    class Tier(models.TextChoices):
        FREE = 'free', _('Free')
        PRO = 'pro', _('Pro')
        ENTERPRISE = 'enterprise', _('Enterprise')

    name = models.CharField(max_length=50)
    tier = models.CharField(max_length=20, choices=Tier.choices, unique=True)
    price_monthly = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    # Limits — 0 means unlimited
    max_projects = models.IntegerField(
        default=1,
        help_text='Maximum number of active projects. 0 = unlimited.',
    )
    max_members = models.IntegerField(
        default=3,
        help_text='Maximum number of organisation members. 0 = unlimited.',
    )
    deadline_emails = models.BooleanField(
        default=False,
        help_text='Whether deadline reminder emails are sent for this plan.',
    )

    # Stripe
    stripe_price_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['price_monthly']
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'

    def __str__(self):
        return self.name

    @property
    def is_free(self):
        return self.tier == self.Tier.FREE

    @property
    def is_unlimited_projects(self):
        return self.max_projects == 0

    @property
    def is_unlimited_members(self):
        return self.max_members == 0


class Organisation(TimeStampedModel):
    """An account / tenant on the platform. Every registered user belongs to one."""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        SUSPENDED = 'suspended', _('Suspended')
        CANCELLED = 'cancelled', _('Cancelled')

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True)
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='organisations',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    # Stripe billing identifiers
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    subscription_current_period_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Organisation'
        verbose_name_plural = 'Organisations'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)
            slug = base
            n = 1
            while Organisation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    # --- Limit helpers ---

    @property
    def active_member_count(self):
        return self.memberships.filter(is_active=True).count()

    @property
    def project_count(self):
        return self.projects.count()

    def can_add_project(self):
        if not self.plan:
            return False
        if self.plan.is_unlimited_projects:
            return True
        return self.project_count < self.plan.max_projects

    def can_add_member(self):
        if not self.plan:
            return False
        if self.plan.is_unlimited_members:
            return True
        return self.active_member_count < self.plan.max_members

    @property
    def plan_name(self):
        return self.plan.name if self.plan else 'No Plan'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE


class OrganisationMembership(TimeStampedModel):
    """Links a User to an Organisation with an org-level role."""

    class Role(models.TextChoices):
        OWNER = 'owner', _('Owner')
        ADMIN = 'admin', _('Admin')
        MEMBER = 'member', _('Member')

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    org_role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name='Organisation Role',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [['organisation', 'user']]
        ordering = ['organisation', 'user__last_name']
        verbose_name = 'Organisation Membership'
        verbose_name_plural = 'Organisation Memberships'

    def __str__(self):
        return f'{self.user} @ {self.organisation} ({self.org_role})'

    @property
    def is_owner(self):
        return self.org_role == self.Role.OWNER

    @property
    def is_org_admin(self):
        return self.org_role in (self.Role.OWNER, self.Role.ADMIN)
