"""Management command to seed the three default subscription plans."""

from django.core.management.base import BaseCommand
from apps.subscriptions.models import SubscriptionPlan


PLANS = [
    {
        'tier': SubscriptionPlan.Tier.FREE,
        'name': 'Free',
        'price_monthly': '0.00',
        'max_projects': 1,
        'max_members': 3,
        'deadline_emails': False,
    },
    {
        'tier': SubscriptionPlan.Tier.PRO,
        'name': 'Pro',
        'price_monthly': '49.00',
        'max_projects': 1,
        'max_members': 10,
        'deadline_emails': True,
    },
    {
        'tier': SubscriptionPlan.Tier.ENTERPRISE,
        'name': 'Enterprise',
        'price_monthly': '199.00',
        'max_projects': 0,   # unlimited
        'max_members': 0,    # unlimited
        'deadline_emails': True,
    },
]


class Command(BaseCommand):
    help = 'Seed the three default subscription plans (Free / Pro / Enterprise).'

    def handle(self, *args, **options):
        for data in PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(
                tier=data['tier'],
                defaults=data,
            )
            verb = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(f'{verb}: {plan.name} plan'))
        self.stdout.write(self.style.SUCCESS('Done.'))
