"""Send colorful HTML credential emails (once per person)."""

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_credential_emails(recipients, login_url):
    """
    Send one email per recipient dict.
    Skips recipients without email. Deduplicates by profile_id.
    """
    seen_ids = set()
    sent = 0
    skipped_no_email = 0
    skipped_duplicate = 0
    failed = []

    for person in recipients:
        pid = person.get('profile_id')
        if pid in seen_ids:
            skipped_duplicate += 1
            continue
        seen_ids.add(pid)

        email = (person.get('email') or '').strip()
        if not email:
            skipped_no_email += 1
            continue

        try:
            html = render_to_string('marksheet/emails/credential_email.html', {
                'person': person,
                'login_url': login_url,
                'site_name': 'ICRAET 2026',
                'org_name': 'LJIET — Lok Jagruti University',
            })
            subject = (
                f"ICRAET 2026 — Your {person.get('role_label', 'Portal')} Login Credentials"
            )
            send_mail(
                subject=subject,
                message='Please view this email in an HTML-capable email client.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html,
                fail_silently=False,
            )
            sent += 1
        except Exception as exc:
            failed.append({'name': person.get('name', ''), 'email': email, 'error': str(exc)})

    return {
        'sent': sent,
        'skipped_no_email': skipped_no_email,
        'skipped_duplicate': skipped_duplicate,
        'failed': failed,
    }
