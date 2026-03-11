from celery import shared_task
from django.utils import timezone


@shared_task
def check_deadlines():
    """Notify if Early Warnings have been open for more than 2 weeks without action.
    Only sends emails if the project's organisation plan includes deadline_emails."""
    from .models import EarlyWarning
    from django.core.mail import send_mail
    from django.conf import settings

    two_weeks_ago = timezone.now() - timezone.timedelta(weeks=2)
    stale = EarlyWarning.objects.filter(
        status='open',
        created_at__lte=two_weeks_ago,
    ).select_related('project', 'raised_by', 'project__project_manager', 'project__organisation__plan')

    for ew in stale:
        # Gate on plan
        org = getattr(ew.project, 'organisation', None)
        plan = getattr(org, 'plan', None) if org else None
        if not plan or not plan.deadline_emails:
            continue

        pm = ew.project.project_manager
        if pm and pm.email:
            send_mail(
                subject=f'[NEC4] Early Warning {ew.reference} — Action Required',
                message=(
                    f'Early Warning {ew.reference} on project {ew.project} '
                    f'has been open for over 2 weeks and requires attention.\n\n'
                    f'Description: {ew.description}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pm.email],
                fail_silently=True,
            )
