from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


def _org_has_deadline_emails(project):
    """Return True if the project's organisation plan allows deadline emails."""
    org = getattr(project, 'organisation', None)
    if org is None:
        return False
    plan = getattr(org, 'plan', None)
    return bool(plan and plan.deadline_emails)


@shared_task
def check_deadlines():
    """
    Hourly task that:
    1. Notifies PMs of CEs where the 8-week reply deadline is approaching (within 1 week).
    2. Flags CEs as 'assumed' if PM has failed to respond within 8 weeks (Clause 61.4).
    """
    from .models import CompensationEvent

    now = timezone.now()
    one_week_from_now = now + timezone.timedelta(weeks=1)

    # Approaching deadline — warn PM (only for orgs with deadline_emails)
    approaching = CompensationEvent.objects.filter(
        state='notified',
        notification_date__lte=one_week_from_now - timezone.timedelta(weeks=7),
        notification_date__gt=now - timezone.timedelta(weeks=8),
    ).select_related('project__project_manager', 'project__organisation__plan')

    for ce in approaching:
        if not _org_has_deadline_emails(ce.project):
            continue
        pm = ce.project.project_manager
        if pm and pm.email:
            send_mail(
                subject=f'[NEC4] CE {ce.reference} — 8-Week Deadline Approaching',
                message=(
                    f'Compensation Event {ce.reference} on project {ce.project} '
                    f'requires your response by {ce.pm_reply_deadline.strftime("%d %b %Y")}.\n\n'
                    f'Description: {ce.description}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[pm.email],
                fail_silently=True,
            )

    # Overdue — attempt to auto-assume (regardless of plan)
    overdue = CompensationEvent.objects.filter(
        state='notified',
        notification_date__lte=now - timezone.timedelta(weeks=8),
    )
    for ce in overdue:
        try:
            ce.assume_ce()
            ce.save()
        except Exception:
            pass

            pass
