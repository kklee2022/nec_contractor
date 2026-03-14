"""
Email notifications for NEC4 platform events.

Recipients = all active Contractor staff who are project members.
In development the console backend prints emails instead of sending them.
"""

from django.conf import settings
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _recipient_list(project):
    """Return email addresses of all active contractor-role project members."""
    return list(
        project.members
        .filter(role='contractor', is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


def _send(subject, template, context, project):
    recipients = _recipient_list(project)
    if not recipients:
        return
    html_body = render_to_string(template, context)
    plain_body = strip_tags(html_body)
    from_email = settings.DEFAULT_FROM_EMAIL
    messages = [(subject, plain_body, from_email, [r]) for r in recipients]
    send_mass_mail(messages, fail_silently=True)


# ── Early Warning notifications ─────────────────────────────────────────────

def notify_ew_raised(ew):
    _send(
        subject=f'[NEC4] Early Warning raised: {ew.reference} — {ew.project.reference}',
        template='notifications/ew_raised.html',
        context={'ew': ew},
        project=ew.project,
    )


def notify_ew_status_changed(ew, old_status):
    _send(
        subject=f'[NEC4] Early Warning status updated: {ew.reference} → {ew.get_status_display()}',
        template='notifications/ew_status_changed.html',
        context={'ew': ew, 'old_status': old_status},
        project=ew.project,
    )


# ── Compensation Event notifications ────────────────────────────────────────

def notify_ce_notified(ce):
    _send(
        subject=f'[NEC4] CE notified: {ce.reference} — {ce.project.reference}',
        template='notifications/ce_notified.html',
        context={'ce': ce},
        project=ce.project,
    )


def notify_ce_state_changed(ce, old_state):
    _send(
        subject=f'[NEC4] CE status updated: {ce.reference} → {ce.state.replace("_", " ").title()}',
        template='notifications/ce_state_changed.html',
        context={'ce': ce, 'old_state': old_state},
        project=ce.project,
    )


# ── Communication notifications ──────────────────────────────────────────────

def notify_communication_logged(comm):
    _send(
        subject=f'[NEC4] Communication logged: {comm.reference} — {comm.project.reference}',
        template='notifications/comm_logged.html',
        context={'comm': comm},
        project=comm.project,
    )
