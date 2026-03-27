import logging

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Campaign, CampaignEmail, CampaignSchedule
from .serializers import (
    CampaignListSerializer,
    CampaignDetailSerializer,
    CampaignEmailSerializer,
    CampaignSendSerializer,
    ABTestSerializer,
    CampaignScheduleSerializer,
)
from .tasks import send_campaign_task, send_test_email_task
from .services import CampaignService
from utils.exceptions import CampaignNotReady

logger = logging.getLogger(__name__)


class CampaignViewSet(viewsets.ModelViewSet):
    """Full CRUD for campaigns with send/schedule actions."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "campaign_type"]
    search_fields = ["name", "subject"]
    ordering_fields = ["name", "created_at", "sent_at", "total_sent"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return CampaignListSerializer
        return CampaignDetailSerializer

    def get_queryset(self):
        return Campaign.objects.filter(
            organization=self.request.user.organization
        ).select_related("schedule", "created_by").prefetch_related(
            "contact_lists", "segments", "exclude_lists"
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        """Send a campaign immediately or schedule it."""
        campaign = self.get_object()
        serializer = CampaignSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Handle test email
        test_email = serializer.validated_data.get("test_email")
        if test_email:
            send_test_email_task.delay(str(campaign.id), test_email)
            return Response({"message": f"Test email queued for {test_email}"})

        try:
            CampaignService.validate_campaign_for_sending(campaign)
        except CampaignNotReady as e:
            return Response(
                {"error": e.message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if serializer.validated_data.get("send_immediately", True):
            send_campaign_task.delay(str(campaign.id))
            campaign.status = Campaign.Status.SENDING
            campaign.save(update_fields=["status"])
            return Response({"message": "Campaign queued for sending."})
        else:
            scheduled_at = serializer.validated_data.get("scheduled_at")
            if not scheduled_at:
                return Response(
                    {"error": "scheduled_at is required for scheduled sends."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            CampaignSchedule.objects.update_or_create(
                campaign=campaign,
                defaults={
                    "schedule_type": CampaignSchedule.ScheduleType.SCHEDULED,
                    "scheduled_at": scheduled_at,
                },
            )
            campaign.status = Campaign.Status.SCHEDULED
            campaign.save(update_fields=["status"])
            return Response({
                "message": f"Campaign scheduled for {scheduled_at.isoformat()}"
            })

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause a sending campaign."""
        campaign = self.get_object()
        if campaign.status != Campaign.Status.SENDING:
            return Response(
                {"error": "Only sending campaigns can be paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.status = Campaign.Status.PAUSED
        campaign.save(update_fields=["status"])
        return Response({"message": "Campaign paused."})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """Resume a paused campaign."""
        campaign = self.get_object()
        if campaign.status != Campaign.Status.PAUSED:
            return Response(
                {"error": "Only paused campaigns can be resumed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        send_campaign_task.delay(str(campaign.id))
        campaign.status = Campaign.Status.SENDING
        campaign.save(update_fields=["status"])
        return Response({"message": "Campaign resumed."})

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a scheduled or sending campaign."""
        campaign = self.get_object()
        if campaign.status not in [Campaign.Status.SCHEDULED, Campaign.Status.SENDING, Campaign.Status.PAUSED]:
            return Response(
                {"error": "Campaign cannot be cancelled from its current status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.status = Campaign.Status.CANCELLED
        campaign.save(update_fields=["status"])

        # Cancel unsent emails
        CampaignEmail.objects.filter(
            campaign=campaign,
            status=CampaignEmail.Status.QUEUED,
        ).delete()

        return Response({"message": "Campaign cancelled."})

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a campaign."""
        original = self.get_object()

        new_campaign = Campaign.objects.create(
            organization=original.organization,
            name=f"{original.name} (Copy)",
            subject=original.subject,
            preview_text=original.preview_text,
            from_name=original.from_name,
            from_email=original.from_email,
            reply_to=original.reply_to,
            html_content=original.html_content,
            plain_text_content=original.plain_text_content,
            template=original.template,
            campaign_type=original.campaign_type,
            track_opens=original.track_opens,
            track_clicks=original.track_clicks,
            created_by=request.user,
        )

        new_campaign.contact_lists.set(original.contact_lists.all())
        new_campaign.segments.set(original.segments.all())
        new_campaign.exclude_lists.set(original.exclude_lists.all())

        return Response(
            CampaignDetailSerializer(new_campaign, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def emails(self, request, pk=None):
        """List individual emails in a campaign."""
        campaign = self.get_object()
        emails = CampaignEmail.objects.filter(campaign=campaign).select_related("contact")

        # Filter by status
        email_status = request.query_params.get("status")
        if email_status:
            emails = emails.filter(status=email_status)

        page = self.paginate_queryset(emails)
        if page is not None:
            serializer = CampaignEmailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CampaignEmailSerializer(emails, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get detailed campaign statistics."""
        campaign = self.get_object()

        stats = {
            "total_recipients": campaign.total_recipients,
            "total_sent": campaign.total_sent,
            "total_delivered": campaign.total_delivered,
            "total_opens": campaign.total_opens,
            "unique_opens": campaign.unique_opens,
            "total_clicks": campaign.total_clicks,
            "unique_clicks": campaign.unique_clicks,
            "total_bounces": campaign.total_bounces,
            "total_unsubscribes": campaign.total_unsubscribes,
            "open_rate": campaign.open_rate,
            "click_rate": campaign.click_rate,
            "bounce_rate": campaign.bounce_rate,
            "unsubscribe_rate": campaign.unsubscribe_rate,
            "status_breakdown": {},
        }

        # Status breakdown
        from django.db.models import Count
        breakdown = (
            CampaignEmail.objects.filter(campaign=campaign)
            .values("status")
            .annotate(count=Count("id"))
        )
        stats["status_breakdown"] = {
            item["status"]: item["count"] for item in breakdown
        }

        # A/B test stats if applicable
        try:
            ab_test = campaign.ab_test
            stats["ab_test"] = ABTestSerializer(ab_test).data
        except Exception:
            pass

        return Response(stats)
