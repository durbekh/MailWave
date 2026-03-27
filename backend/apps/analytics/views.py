import logging
from datetime import timedelta

from django.db.models import Sum, Avg, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campaigns.models import Campaign, CampaignEmail
from apps.contacts.models import Contact
from apps.automation.models import AutomationWorkflow

from .models import DailyStats, CampaignClickEvent, CampaignOpenEvent, LinkClickSummary
from .serializers import (
    DailyStatsSerializer,
    CampaignClickEventSerializer,
    CampaignOpenEventSerializer,
    LinkClickSummarySerializer,
    DashboardSummarySerializer,
    DateRangeSerializer,
)
from utils.email_sender import TRANSPARENT_PIXEL_GIF

logger = logging.getLogger(__name__)


class DashboardView(APIView):
    """Main dashboard analytics endpoint."""

    def get(self, request):
        org = request.user.organization
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Contact stats
        total_contacts = Contact.objects.filter(organization=org).count()
        active_contacts = Contact.objects.filter(
            organization=org, status=Contact.Status.SUBSCRIBED,
        ).count()

        # Campaign stats
        total_campaigns = Campaign.objects.filter(organization=org).count()
        campaigns_sent_this_month = Campaign.objects.filter(
            organization=org,
            status=Campaign.Status.SENT,
            sent_at__gte=month_start,
        ).count()

        # Email stats
        emails_sent_this_month = org.emails_sent_this_month

        # Average rates from recent campaigns
        recent_campaigns = Campaign.objects.filter(
            organization=org,
            status=Campaign.Status.SENT,
            total_sent__gt=0,
        ).order_by("-sent_at")[:20]

        avg_open_rate = 0
        avg_click_rate = 0
        if recent_campaigns.exists():
            rates = [(c.open_rate, c.click_rate) for c in recent_campaigns]
            avg_open_rate = round(sum(r[0] for r in rates) / len(rates), 2)
            avg_click_rate = round(sum(r[1] for r in rates) / len(rates), 2)

        # Automation stats
        active_automations = AutomationWorkflow.objects.filter(
            organization=org,
            status=AutomationWorkflow.Status.ACTIVE,
        ).count()

        # Monthly growth
        contacts_added_this_month = Contact.objects.filter(
            organization=org,
            created_at__gte=month_start,
        ).count()

        unsubscribes_this_month = Contact.objects.filter(
            organization=org,
            unsubscribed_at__gte=month_start,
        ).count()

        data = {
            "total_contacts": total_contacts,
            "active_contacts": active_contacts,
            "total_campaigns": total_campaigns,
            "campaigns_sent_this_month": campaigns_sent_this_month,
            "emails_sent_this_month": emails_sent_this_month,
            "average_open_rate": avg_open_rate,
            "average_click_rate": avg_click_rate,
            "active_automations": active_automations,
            "contacts_added_this_month": contacts_added_this_month,
            "unsubscribes_this_month": unsubscribes_this_month,
        }

        serializer = DashboardSummarySerializer(data)
        return Response(serializer.data)


class DailyStatsView(APIView):
    """Get daily stats for a date range."""

    def get(self, request):
        org = request.user.organization

        start_date = request.query_params.get(
            "start_date",
            (timezone.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        )
        end_date = request.query_params.get(
            "end_date",
            timezone.now().strftime("%Y-%m-%d"),
        )

        range_serializer = DateRangeSerializer(data={
            "start_date": start_date,
            "end_date": end_date,
        })
        range_serializer.is_valid(raise_exception=True)

        stats = DailyStats.objects.filter(
            organization=org,
            date__gte=range_serializer.validated_data["start_date"],
            date__lte=range_serializer.validated_data["end_date"],
        ).order_by("date")

        # Fill in missing dates with zero values
        serializer = DailyStatsSerializer(stats, many=True)
        return Response(serializer.data)


class CampaignAnalyticsView(APIView):
    """Detailed analytics for a specific campaign."""

    def get(self, request, campaign_id):
        org = request.user.organization

        try:
            campaign = Campaign.objects.get(
                id=campaign_id, organization=org,
            )
        except Campaign.DoesNotExist:
            return Response(
                {"error": "Campaign not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Overall stats
        stats = {
            "campaign_id": str(campaign.id),
            "campaign_name": campaign.name,
            "status": campaign.status,
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
        }

        # Device breakdown
        open_events = CampaignOpenEvent.objects.filter(
            campaign_email__campaign=campaign,
        )
        device_breakdown = open_events.values("device_type").annotate(
            count=Count("id"),
        ).order_by("-count")
        stats["device_breakdown"] = list(device_breakdown)

        # Geographic breakdown (top 10 countries)
        geo_breakdown = open_events.exclude(country="").values("country").annotate(
            count=Count("id"),
        ).order_by("-count")[:10]
        stats["geographic_breakdown"] = list(geo_breakdown)

        # Link click summary
        link_summaries = LinkClickSummary.objects.filter(campaign=campaign)
        stats["link_clicks"] = LinkClickSummarySerializer(
            link_summaries, many=True,
        ).data

        # Hourly open distribution
        opens_by_hour = open_events.extra(
            select={"hour": "EXTRACT(HOUR FROM opened_at)"},
        ).values("hour").annotate(count=Count("id")).order_by("hour")
        stats["opens_by_hour"] = list(opens_by_hour)

        return Response(stats)


@api_view(["GET"])
@permission_classes([AllowAny])
def track_open(request):
    """
    Track email opens via a 1x1 transparent pixel.
    This endpoint is called when the tracking pixel image is loaded.
    """
    campaign_email_id = request.query_params.get("ceid")
    if not campaign_email_id or campaign_email_id == "test-preview":
        return HttpResponse(
            TRANSPARENT_PIXEL_GIF,
            content_type="image/gif",
        )

    try:
        campaign_email = CampaignEmail.objects.get(id=campaign_email_id)
    except CampaignEmail.DoesNotExist:
        return HttpResponse(TRANSPARENT_PIXEL_GIF, content_type="image/gif")

    # Update campaign email stats
    campaign_email.open_count += 1
    if not campaign_email.opened_at:
        campaign_email.opened_at = timezone.now()
        campaign_email.status = CampaignEmail.Status.OPENED

    campaign_email.save(update_fields=["open_count", "opened_at", "status"])

    # Parse user agent for device info
    user_agent_str = request.META.get("HTTP_USER_AGENT", "")
    ip = _get_client_ip(request)
    device_info = _parse_user_agent(user_agent_str)

    CampaignOpenEvent.objects.create(
        campaign_email=campaign_email,
        user_agent=user_agent_str,
        ip_address=ip,
        device_type=device_info.get("device_type", ""),
        browser=device_info.get("browser", ""),
        os=device_info.get("os", ""),
    )

    # Update contact stats
    contact = campaign_email.contact
    contact.total_opens += 1
    contact.last_opened_at = timezone.now()
    contact.save(update_fields=["total_opens", "last_opened_at"])

    return HttpResponse(TRANSPARENT_PIXEL_GIF, content_type="image/gif")


@api_view(["GET"])
@permission_classes([AllowAny])
def track_click(request):
    """
    Track link clicks and redirect to the original URL.
    """
    from django.shortcuts import redirect

    campaign_email_id = request.query_params.get("ceid")
    link_id = request.query_params.get("lid", "")
    original_url = request.query_params.get("url", "/")

    if not campaign_email_id:
        return redirect(original_url)

    try:
        campaign_email = CampaignEmail.objects.get(id=campaign_email_id)
    except CampaignEmail.DoesNotExist:
        return redirect(original_url)

    # Update campaign email click stats
    campaign_email.click_count += 1
    if not campaign_email.clicked_at:
        campaign_email.clicked_at = timezone.now()
        campaign_email.status = CampaignEmail.Status.CLICKED

    campaign_email.save(update_fields=["click_count", "clicked_at", "status"])

    # Parse user agent
    user_agent_str = request.META.get("HTTP_USER_AGENT", "")
    ip = _get_client_ip(request)
    device_info = _parse_user_agent(user_agent_str)

    CampaignClickEvent.objects.create(
        campaign_email=campaign_email,
        url=original_url,
        link_id=link_id,
        user_agent=user_agent_str,
        ip_address=ip,
        device_type=device_info.get("device_type", ""),
        browser=device_info.get("browser", ""),
        os=device_info.get("os", ""),
    )

    # Update contact stats
    contact = campaign_email.contact
    contact.total_clicks += 1
    contact.last_clicked_at = timezone.now()
    contact.save(update_fields=["total_clicks", "last_clicked_at"])

    # Update link click summary
    LinkClickSummary.objects.update_or_create(
        campaign=campaign_email.campaign,
        url=original_url,
        defaults={"link_id": link_id, "last_clicked_at": timezone.now()},
    )
    summary = LinkClickSummary.objects.get(
        campaign=campaign_email.campaign, url=original_url,
    )
    summary.total_clicks += 1
    # Count unique clicks for this link
    unique = CampaignClickEvent.objects.filter(
        campaign_email__campaign=campaign_email.campaign,
        url=original_url,
    ).values("campaign_email__contact").distinct().count()
    summary.unique_clicks = unique
    summary.save(update_fields=["total_clicks", "unique_clicks"])

    return redirect(original_url)


@api_view(["GET"])
@permission_classes([AllowAny])
def unsubscribe_view(request, token):
    """Handle unsubscribe requests from email links."""
    try:
        contact = Contact.objects.get(unsubscribe_token=token)
    except Contact.DoesNotExist:
        return Response({"error": "Invalid unsubscribe link."}, status=404)

    contact.status = Contact.Status.UNSUBSCRIBED
    contact.unsubscribed_at = timezone.now()
    contact.save(update_fields=["status", "unsubscribed_at"])

    logger.info("Contact %s unsubscribed via link", contact.email)

    return Response({
        "message": "You have been successfully unsubscribed.",
        "email": contact.email,
    })


def _get_client_ip(request):
    """Extract client IP from request headers."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _parse_user_agent(user_agent_str):
    """Parse user agent string for device/browser/OS info."""
    ua = user_agent_str.lower()
    result = {"device_type": "desktop", "browser": "", "os": ""}

    # Device type
    if "mobile" in ua or "android" in ua or "iphone" in ua:
        result["device_type"] = "mobile"
    elif "tablet" in ua or "ipad" in ua:
        result["device_type"] = "tablet"

    # Browser
    if "chrome" in ua and "edg" not in ua:
        result["browser"] = "Chrome"
    elif "firefox" in ua:
        result["browser"] = "Firefox"
    elif "safari" in ua and "chrome" not in ua:
        result["browser"] = "Safari"
    elif "edg" in ua:
        result["browser"] = "Edge"
    elif "msie" in ua or "trident" in ua:
        result["browser"] = "Internet Explorer"

    # OS
    if "windows" in ua:
        result["os"] = "Windows"
    elif "macintosh" in ua or "mac os" in ua:
        result["os"] = "macOS"
    elif "linux" in ua and "android" not in ua:
        result["os"] = "Linux"
    elif "android" in ua:
        result["os"] = "Android"
    elif "iphone" in ua or "ipad" in ua:
        result["os"] = "iOS"

    return result
