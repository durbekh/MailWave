"""
Campaign business logic and services.
"""

import logging
import random
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.contacts.models import Contact
from utils.email_sender import email_sender
from utils.exceptions import CampaignNotReady

from .models import Campaign, CampaignEmail, ABTest

logger = logging.getLogger(__name__)


class CampaignService:
    """Service class for campaign operations."""

    @staticmethod
    def validate_campaign_for_sending(campaign):
        """Validate that a campaign is ready to send."""
        errors = []

        if not campaign.subject:
            errors.append("Campaign must have a subject line.")

        if not campaign.html_content:
            errors.append("Campaign must have email content.")

        if not campaign.contact_lists.exists() and not campaign.segments.exists():
            errors.append("Campaign must have at least one contact list or segment.")

        if campaign.status not in [Campaign.Status.DRAFT, Campaign.Status.SCHEDULED]:
            errors.append(f"Campaign cannot be sent from {campaign.status} status.")

        org = campaign.organization
        if org.email_limit_reached:
            errors.append("Organization has reached its monthly email limit.")

        if errors:
            raise CampaignNotReady("; ".join(errors))

        return True

    @staticmethod
    def prepare_campaign_emails(campaign):
        """Create CampaignEmail records for all recipients."""
        recipients = campaign.get_recipients()
        total = recipients.count()

        if total == 0:
            raise CampaignNotReady("No eligible recipients found for this campaign.")

        # Check if campaign emails already exist
        existing_count = CampaignEmail.objects.filter(campaign=campaign).count()
        if existing_count > 0:
            logger.info(
                "Campaign %s already has %d emails, skipping preparation",
                campaign.id, existing_count,
            )
            return existing_count

        campaign_emails = []

        # Handle A/B test variant assignment
        ab_test = getattr(campaign, "ab_test", None)
        if ab_test and campaign.campaign_type == Campaign.CampaignType.AB_TEST:
            test_size = int(total * (ab_test.test_percentage / 100))
            recipient_list = list(recipients.values_list("id", flat=True))
            random.shuffle(recipient_list)

            test_recipients = recipient_list[:test_size]
            remaining_recipients = recipient_list[test_size:]

            # Split test group evenly between A and B
            half = len(test_recipients) // 2
            variant_a_ids = set(test_recipients[:half])
            variant_b_ids = set(test_recipients[half:])

            for contact_id in recipient_list:
                if contact_id in variant_a_ids:
                    variant = "A"
                    subject = ab_test.variant_a_subject or campaign.subject
                elif contact_id in variant_b_ids:
                    variant = "B"
                    subject = ab_test.variant_b_subject or campaign.subject
                else:
                    variant = ""  # Will be assigned winner later
                    subject = campaign.subject

                campaign_emails.append(
                    CampaignEmail(
                        campaign=campaign,
                        contact_id=contact_id,
                        ab_variant=variant,
                        subject_used=subject,
                    )
                )
        else:
            for contact in recipients.only("id"):
                campaign_emails.append(
                    CampaignEmail(
                        campaign=campaign,
                        contact=contact,
                        subject_used=campaign.subject,
                    )
                )

        CampaignEmail.objects.bulk_create(campaign_emails, batch_size=1000)

        campaign.total_recipients = total
        campaign.save(update_fields=["total_recipients"])

        logger.info(
            "Prepared %d emails for campaign %s", total, campaign.id,
        )

        return total

    @staticmethod
    def send_campaign_emails(campaign, variant_filter=None):
        """Send queued campaign emails."""
        from_email = campaign.from_email or campaign.organization.default_from_email
        from_name = campaign.from_name or campaign.organization.default_from_name

        queryset = CampaignEmail.objects.filter(
            campaign=campaign,
            status=CampaignEmail.Status.QUEUED,
        ).select_related("contact")

        if variant_filter:
            queryset = queryset.filter(ab_variant=variant_filter)

        # Get schedule settings for batch size
        schedule = getattr(campaign, "schedule", None)
        batch_size = schedule.batch_size if schedule else 500

        total_sent = 0
        total_failed = 0

        # Process in batches
        while True:
            batch = list(queryset[:batch_size])
            if not batch:
                break

            email_batch = []
            for campaign_email in batch:
                contact = campaign_email.contact

                # Determine content based on A/B variant
                html_content = campaign.html_content
                ab_test = getattr(campaign, "ab_test", None)
                if ab_test and campaign_email.ab_variant:
                    if campaign_email.ab_variant == "B" and ab_test.variant_b_content:
                        html_content = ab_test.variant_b_content

                unsubscribe_url = (
                    f"http://{campaign.organization.default_from_email.split('@')[-1] if campaign.organization.default_from_email else 'localhost'}"
                    f"/unsubscribe/{contact.unsubscribe_token}/"
                )

                email_batch.append({
                    "to_email": contact.email,
                    "subject": campaign_email.subject_used,
                    "html_content": html_content,
                    "campaign_email_id": str(campaign_email.id),
                    "contact_data": contact.to_merge_dict(),
                    "unsubscribe_url": unsubscribe_url,
                })

            results = email_sender.send_batch(
                email_batch,
                organization_id=str(campaign.organization_id),
            )

            # Update campaign email statuses
            now = timezone.now()
            sent_ids = []
            for i, campaign_email in enumerate(batch):
                if i < results["sent"]:
                    campaign_email.status = CampaignEmail.Status.SENT
                    campaign_email.sent_at = now
                    sent_ids.append(campaign_email.id)
                else:
                    if i - results["sent"] < results["failed"]:
                        campaign_email.status = CampaignEmail.Status.FAILED
                        error_info = results["errors"][i - results["sent"]] if (i - results["sent"]) < len(results["errors"]) else {}
                        campaign_email.error_message = error_info.get("error", "Unknown error")

            CampaignEmail.objects.bulk_update(
                batch, ["status", "sent_at", "error_message"], batch_size=500,
            )

            total_sent += results["sent"]
            total_failed += results["failed"]

            # Update campaign stats
            campaign.total_sent = CampaignEmail.objects.filter(
                campaign=campaign,
                status__in=[
                    CampaignEmail.Status.SENT,
                    CampaignEmail.Status.DELIVERED,
                    CampaignEmail.Status.OPENED,
                    CampaignEmail.Status.CLICKED,
                ],
            ).count()
            campaign.save(update_fields=["total_sent"])

            # Update organization email count
            campaign.organization.emails_sent_this_month += results["sent"]
            campaign.organization.save(update_fields=["emails_sent_this_month"])

            logger.info(
                "Batch sent for campaign %s: sent=%d, failed=%d",
                campaign.id, results["sent"], results["failed"],
            )

        return {"sent": total_sent, "failed": total_failed}

    @staticmethod
    def evaluate_ab_test(campaign):
        """Evaluate A/B test results and send winner to remaining recipients."""
        try:
            ab_test = campaign.ab_test
        except ABTest.DoesNotExist:
            return

        if ab_test.winner_variant:
            return  # Already determined

        # Update A/B stats
        ab_test.variant_a_sent = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="A",
            status__in=[CampaignEmail.Status.SENT, CampaignEmail.Status.DELIVERED,
                       CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED],
        ).count()
        ab_test.variant_a_opens = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="A",
            status__in=[CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED],
        ).count()
        ab_test.variant_a_clicks = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="A",
            status=CampaignEmail.Status.CLICKED,
        ).count()
        ab_test.variant_b_sent = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="B",
            status__in=[CampaignEmail.Status.SENT, CampaignEmail.Status.DELIVERED,
                       CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED],
        ).count()
        ab_test.variant_b_opens = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="B",
            status__in=[CampaignEmail.Status.OPENED, CampaignEmail.Status.CLICKED],
        ).count()
        ab_test.variant_b_clicks = CampaignEmail.objects.filter(
            campaign=campaign, ab_variant="B",
            status=CampaignEmail.Status.CLICKED,
        ).count()

        # Determine winner
        winner = ab_test.determine_winner()
        ab_test.winner_variant = winner
        ab_test.winner_selected_at = timezone.now()
        ab_test.save()

        # Update remaining emails with winner content
        winner_subject = (
            ab_test.variant_a_subject if winner == "A"
            else ab_test.variant_b_subject
        ) or campaign.subject

        CampaignEmail.objects.filter(
            campaign=campaign,
            ab_variant="",
            status=CampaignEmail.Status.QUEUED,
        ).update(
            ab_variant=winner,
            subject_used=winner_subject,
        )

        # Send to remaining recipients
        CampaignService.send_campaign_emails(campaign, variant_filter=winner)

        logger.info(
            "A/B test winner for campaign %s: variant %s", campaign.id, winner,
        )
