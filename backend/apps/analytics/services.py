"""
Analytics aggregation and reporting services.
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.db.models import Count, Sum, Q
from django.utils import timezone

from apps.accounts.models import Organization
from apps.campaigns.models import Campaign, CampaignEmail
from apps.contacts.models import Contact
from .models import DailyStats

logger = logging.getLogger(__name__)


@shared_task
def aggregate_daily_stats():
    """
    Aggregate daily statistics for all organizations.
    Runs periodically via Celery Beat.
    """
    today = date.today()

    organizations = Organization.objects.filter(is_active=True)

    for org in organizations:
        try:
            _aggregate_org_daily_stats(org, today)
        except Exception as e:
            logger.error(
                "Failed to aggregate stats for org %s: %s",
                org.id, str(e), exc_info=True,
            )

    logger.info("Daily stats aggregation completed for %d organizations", organizations.count())


def _aggregate_org_daily_stats(org, target_date):
    """Aggregate stats for a specific organization and date."""
    day_start = timezone.make_aware(
        timezone.datetime.combine(target_date, timezone.datetime.min.time())
    )
    day_end = day_start + timedelta(days=1)

    # Campaign email stats for the day
    campaign_emails = CampaignEmail.objects.filter(
        campaign__organization=org,
    )

    emails_sent = campaign_emails.filter(
        sent_at__gte=day_start, sent_at__lt=day_end,
    ).count()

    emails_delivered = campaign_emails.filter(
        delivered_at__gte=day_start, delivered_at__lt=day_end,
    ).count()

    emails_opened = campaign_emails.filter(
        opened_at__gte=day_start, opened_at__lt=day_end,
    ).aggregate(total=Sum("open_count"))["total"] or 0

    unique_opens = campaign_emails.filter(
        opened_at__gte=day_start, opened_at__lt=day_end,
    ).count()

    emails_clicked = campaign_emails.filter(
        clicked_at__gte=day_start, clicked_at__lt=day_end,
    ).aggregate(total=Sum("click_count"))["total"] or 0

    unique_clicks = campaign_emails.filter(
        clicked_at__gte=day_start, clicked_at__lt=day_end,
    ).count()

    bounces = campaign_emails.filter(
        bounced_at__gte=day_start, bounced_at__lt=day_end,
    ).count()

    unsubscribes = campaign_emails.filter(
        status=CampaignEmail.Status.UNSUBSCRIBED,
        created_at__gte=day_start, created_at__lt=day_end,
    ).count()

    # Contact stats
    new_contacts = Contact.objects.filter(
        organization=org,
        created_at__gte=day_start, created_at__lt=day_end,
    ).count()

    contacts_unsubscribed = Contact.objects.filter(
        organization=org,
        unsubscribed_at__gte=day_start, unsubscribed_at__lt=day_end,
    ).count()

    # Campaign stats
    campaigns_sent = Campaign.objects.filter(
        organization=org,
        sent_at__gte=day_start, sent_at__lt=day_end,
        status=Campaign.Status.SENT,
    ).count()

    DailyStats.objects.update_or_create(
        organization=org,
        date=target_date,
        defaults={
            "emails_sent": emails_sent,
            "emails_delivered": emails_delivered,
            "emails_opened": emails_opened,
            "unique_opens": unique_opens,
            "emails_clicked": emails_clicked,
            "unique_clicks": unique_clicks,
            "bounces": bounces,
            "unsubscribes": unsubscribes,
            "new_contacts": new_contacts,
            "contacts_unsubscribed": contacts_unsubscribed,
            "campaigns_sent": campaigns_sent,
        },
    )


def generate_campaign_report(campaign_id):
    """Generate a comprehensive report for a campaign."""
    campaign = Campaign.objects.get(id=campaign_id)

    emails = CampaignEmail.objects.filter(campaign=campaign)

    # Status breakdown
    status_breakdown = emails.values("status").annotate(
        count=Count("id"),
    )

    # Hourly distribution of opens
    open_distribution = {}
    opened_emails = emails.filter(opened_at__isnull=False)
    for email in opened_emails:
        hour = email.opened_at.hour
        open_distribution[hour] = open_distribution.get(hour, 0) + 1

    # Top performing links
    from .models import LinkClickSummary
    top_links = LinkClickSummary.objects.filter(
        campaign=campaign,
    ).order_by("-total_clicks")[:10]

    # Engagement segments
    highly_engaged = emails.filter(
        status__in=[CampaignEmail.Status.CLICKED],
    ).count()

    opened_only = emails.filter(
        status=CampaignEmail.Status.OPENED,
    ).count()

    not_engaged = emails.filter(
        status__in=[CampaignEmail.Status.SENT, CampaignEmail.Status.DELIVERED],
    ).count()

    report = {
        "campaign_id": str(campaign.id),
        "campaign_name": campaign.name,
        "sent_at": campaign.sent_at.isoformat() if campaign.sent_at else None,
        "completed_at": campaign.completed_at.isoformat() if campaign.completed_at else None,
        "stats": {
            "total_recipients": campaign.total_recipients,
            "total_sent": campaign.total_sent,
            "total_delivered": campaign.total_delivered,
            "open_rate": campaign.open_rate,
            "click_rate": campaign.click_rate,
            "bounce_rate": campaign.bounce_rate,
            "unsubscribe_rate": campaign.unsubscribe_rate,
        },
        "status_breakdown": {
            item["status"]: item["count"] for item in status_breakdown
        },
        "open_distribution_by_hour": open_distribution,
        "top_links": [
            {
                "url": link.url,
                "total_clicks": link.total_clicks,
                "unique_clicks": link.unique_clicks,
            }
            for link in top_links
        ],
        "engagement_segments": {
            "highly_engaged": highly_engaged,
            "opened_only": opened_only,
            "not_engaged": not_engaged,
        },
    }

    return report


def get_growth_metrics(organization, days=30):
    """Calculate subscriber growth metrics for the dashboard."""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    stats = DailyStats.objects.filter(
        organization=organization,
        date__gte=start_date,
        date__lte=end_date,
    ).order_by("date")

    daily_growth = []
    cumulative_new = 0
    cumulative_unsub = 0

    for stat in stats:
        cumulative_new += stat.new_contacts
        cumulative_unsub += stat.contacts_unsubscribed
        daily_growth.append({
            "date": stat.date.isoformat(),
            "new_contacts": stat.new_contacts,
            "unsubscribes": stat.contacts_unsubscribed,
            "net_growth": stat.new_contacts - stat.contacts_unsubscribed,
            "cumulative_new": cumulative_new,
            "cumulative_unsub": cumulative_unsub,
        })

    totals = stats.aggregate(
        total_new=Sum("new_contacts"),
        total_unsub=Sum("contacts_unsubscribed"),
        total_sent=Sum("emails_sent"),
        total_opens=Sum("unique_opens"),
        total_clicks=Sum("unique_clicks"),
    )

    return {
        "period_days": days,
        "daily_growth": daily_growth,
        "totals": {
            "new_contacts": totals["total_new"] or 0,
            "unsubscribes": totals["total_unsub"] or 0,
            "net_growth": (totals["total_new"] or 0) - (totals["total_unsub"] or 0),
            "emails_sent": totals["total_sent"] or 0,
            "unique_opens": totals["total_opens"] or 0,
            "unique_clicks": totals["total_clicks"] or 0,
        },
    }
