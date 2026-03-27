"""
Celery tasks for account management.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_tokens():
    """
    Clean up expired verification tokens and inactive unverified accounts.
    Runs daily via Celery Beat.
    """
    from .models import User

    expiration_threshold = timezone.now() - timedelta(days=7)

    # Deactivate unverified accounts older than 7 days
    stale_accounts = User.objects.filter(
        email_verified=False,
        is_active=True,
        created_at__lt=expiration_threshold,
    ).exclude(is_superuser=True)

    count = stale_accounts.count()
    if count > 0:
        stale_accounts.update(is_active=False)
        logger.info("Deactivated %d unverified accounts", count)


@shared_task
def reset_monthly_email_counts():
    """
    Reset monthly email counts for all organizations.
    Should run on the 1st of every month.
    """
    from .models import Organization

    updated = Organization.objects.filter(is_active=True).update(
        emails_sent_this_month=0,
    )
    logger.info("Reset email counts for %d organizations", updated)


@shared_task
def send_usage_alert(organization_id):
    """
    Send email alerts when an organization approaches its email limit.
    """
    from .models import Organization, User
    from utils.email_sender import email_sender

    try:
        org = Organization.objects.select_related("plan").get(id=organization_id)
    except Organization.DoesNotExist:
        return

    if not org.plan:
        return

    usage_percent = (org.emails_sent_this_month / org.plan.monthly_email_limit) * 100
    thresholds = [90, 75, 50]

    for threshold in thresholds:
        if usage_percent >= threshold:
            cache_key = f"usage_alert:{org.id}:{threshold}"
            from django.core.cache import cache
            if cache.get(cache_key):
                continue  # Already alerted for this threshold

            # Alert org admins
            admins = User.objects.filter(
                organization=org,
                role__in=[User.Role.OWNER, User.Role.ADMIN],
                is_active=True,
            )

            for admin_user in admins:
                email_sender.send_email(
                    to_email=admin_user.email,
                    subject=f"[MailWave] Email usage at {int(usage_percent)}%",
                    html_content=(
                        f"<h2>Email Usage Alert</h2>"
                        f"<p>Your organization <strong>{org.name}</strong> has used "
                        f"<strong>{int(usage_percent)}%</strong> of your monthly "
                        f"email limit ({org.emails_sent_this_month:,} of "
                        f"{org.plan.monthly_email_limit:,}).</p>"
                        f"<p>Consider upgrading your plan to increase your limit.</p>"
                    ),
                )

            cache.set(cache_key, True, timeout=86400)
            logger.info(
                "Usage alert sent for org %s at %d%%",
                org.id, int(usage_percent),
            )
            break


@shared_task
def generate_org_activity_digest(organization_id):
    """Generate and send a weekly activity digest to org admins."""
    from .models import Organization, User
    from apps.campaigns.models import Campaign
    from apps.contacts.models import Contact
    from utils.email_sender import email_sender

    try:
        org = Organization.objects.get(id=organization_id)
    except Organization.DoesNotExist:
        return

    week_ago = timezone.now() - timedelta(days=7)

    # Gather weekly stats
    campaigns_sent = Campaign.objects.filter(
        organization=org,
        status=Campaign.Status.SENT,
        sent_at__gte=week_ago,
    ).count()

    new_contacts = Contact.objects.filter(
        organization=org,
        created_at__gte=week_ago,
    ).count()

    unsubscribes = Contact.objects.filter(
        organization=org,
        unsubscribed_at__gte=week_ago,
    ).count()

    total_contacts = Contact.objects.filter(
        organization=org,
        status=Contact.Status.SUBSCRIBED,
    ).count()

    admins = User.objects.filter(
        organization=org,
        role__in=[User.Role.OWNER, User.Role.ADMIN],
        is_active=True,
    )

    html_content = (
        f"<h2>Weekly Activity Digest for {org.name}</h2>"
        f"<table style='border-collapse:collapse;'>"
        f"<tr><td style='padding:8px;border:1px solid #ddd;'><strong>Campaigns Sent</strong></td>"
        f"<td style='padding:8px;border:1px solid #ddd;'>{campaigns_sent}</td></tr>"
        f"<tr><td style='padding:8px;border:1px solid #ddd;'><strong>New Contacts</strong></td>"
        f"<td style='padding:8px;border:1px solid #ddd;'>{new_contacts}</td></tr>"
        f"<tr><td style='padding:8px;border:1px solid #ddd;'><strong>Unsubscribes</strong></td>"
        f"<td style='padding:8px;border:1px solid #ddd;'>{unsubscribes}</td></tr>"
        f"<tr><td style='padding:8px;border:1px solid #ddd;'><strong>Total Active Contacts</strong></td>"
        f"<td style='padding:8px;border:1px solid #ddd;'>{total_contacts:,}</td></tr>"
        f"<tr><td style='padding:8px;border:1px solid #ddd;'><strong>Emails Used This Month</strong></td>"
        f"<td style='padding:8px;border:1px solid #ddd;'>{org.emails_sent_this_month:,}</td></tr>"
        f"</table>"
    )

    for admin_user in admins:
        email_sender.send_email(
            to_email=admin_user.email,
            subject=f"[MailWave] Weekly digest for {org.name}",
            html_content=html_content,
        )
