"""
Celery tasks for campaign sending and scheduling.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import Campaign, CampaignEmail, ABTest
from .services import CampaignService
from utils.exceptions import CampaignNotReady

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_campaign_task(self, campaign_id):
    """Send a campaign asynchronously."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found", campaign_id)
        return

    if campaign.status not in [Campaign.Status.DRAFT, Campaign.Status.SCHEDULED]:
        logger.warning(
            "Campaign %s is in %s status, cannot send", campaign_id, campaign.status,
        )
        return

    try:
        # Validate
        CampaignService.validate_campaign_for_sending(campaign)

        # Update status
        campaign.status = Campaign.Status.SENDING
        campaign.sent_at = timezone.now()
        campaign.save(update_fields=["status", "sent_at"])

        # Prepare emails
        CampaignService.prepare_campaign_emails(campaign)

        # Send based on campaign type
        if campaign.campaign_type == Campaign.CampaignType.AB_TEST:
            # Send only to test variants first
            CampaignService.send_campaign_emails(campaign, variant_filter="A")
            CampaignService.send_campaign_emails(campaign, variant_filter="B")

            # Schedule winner evaluation
            ab_test = campaign.ab_test
            evaluate_ab_test_task.apply_async(
                args=[str(campaign_id)],
                countdown=ab_test.test_duration_hours * 3600,
            )
        else:
            # Regular send
            results = CampaignService.send_campaign_emails(campaign)
            logger.info(
                "Campaign %s send results: sent=%d, failed=%d",
                campaign_id, results["sent"], results["failed"],
            )

        # Mark as sent
        campaign.status = Campaign.Status.SENT
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at"])

        logger.info("Campaign %s completed successfully", campaign_id)

    except CampaignNotReady as e:
        campaign.status = Campaign.Status.FAILED
        campaign.save(update_fields=["status"])
        logger.error("Campaign %s not ready: %s", campaign_id, e.message)

    except Exception as e:
        logger.error(
            "Campaign %s failed: %s", campaign_id, str(e), exc_info=True,
        )
        campaign.status = Campaign.Status.FAILED
        campaign.save(update_fields=["status"])
        self.retry(exc=e)


@shared_task
def send_test_email_task(campaign_id, test_email):
    """Send a test email for a campaign."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found", campaign_id)
        return

    from utils.email_sender import email_sender

    contact_data = {
        "email": test_email,
        "first_name": "Test",
        "last_name": "Subscriber",
        "company": "Test Company",
    }

    html = email_sender.prepare_email(
        campaign_email_id="test-preview",
        html_content=campaign.html_content,
        contact_data=contact_data,
        unsubscribe_url="#",
    )

    email_sender.send_email(
        to_email=test_email,
        subject=f"[TEST] {campaign.subject}",
        html_content=html,
        from_email=campaign.from_email,
        from_name=campaign.from_name,
    )

    logger.info("Test email sent for campaign %s to %s", campaign_id, test_email)


@shared_task
def evaluate_ab_test_task(campaign_id):
    """Evaluate A/B test results and send winning variant to remaining recipients."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        logger.error("Campaign %s not found", campaign_id)
        return

    CampaignService.evaluate_ab_test(campaign)


@shared_task
def process_scheduled_campaigns():
    """Process campaigns that are scheduled to send."""
    now = timezone.now()

    scheduled_campaigns = Campaign.objects.filter(
        status=Campaign.Status.SCHEDULED,
        schedule__scheduled_at__lte=now,
    ).select_related("schedule", "organization")

    for campaign in scheduled_campaigns:
        logger.info("Processing scheduled campaign: %s", campaign.id)
        send_campaign_task.delay(str(campaign.id))

    if scheduled_campaigns.exists():
        logger.info("Processed %d scheduled campaigns", scheduled_campaigns.count())


@shared_task
def update_campaign_stats(campaign_id):
    """Update denormalized campaign statistics."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
    except Campaign.DoesNotExist:
        return

    emails = CampaignEmail.objects.filter(campaign=campaign)

    campaign.total_sent = emails.filter(
        status__in=[
            CampaignEmail.Status.SENT, CampaignEmail.Status.DELIVERED,
            CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED,
        ]
    ).count()

    campaign.total_delivered = emails.filter(
        status__in=[
            CampaignEmail.Status.DELIVERED,
            CampaignEmail.Status.OPENED,
            CampaignEmail.Status.CLICKED,
        ]
    ).count()

    campaign.total_opens = emails.aggregate(
        total=models.Sum("open_count")
    )["total"] or 0

    campaign.unique_opens = emails.filter(
        status__in=[CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED]
    ).count()

    campaign.total_clicks = emails.aggregate(
        total=models.Sum("click_count")
    )["total"] or 0

    campaign.unique_clicks = emails.filter(
        status=CampaignEmail.Status.CLICKED
    ).count()

    campaign.total_bounces = emails.filter(
        status=CampaignEmail.Status.BOUNCED
    ).count()

    campaign.total_unsubscribes = emails.filter(
        status=CampaignEmail.Status.UNSUBSCRIBED
    ).count()

    campaign.save(update_fields=[
        "total_sent", "total_delivered", "total_opens", "unique_opens",
        "total_clicks", "unique_clicks", "total_bounces", "total_unsubscribes",
    ])
