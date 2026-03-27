from rest_framework import serializers
from .models import DailyStats, CampaignClickEvent, CampaignOpenEvent, LinkClickSummary


class DailyStatsSerializer(serializers.ModelSerializer):
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    bounce_rate = serializers.ReadOnlyField()

    class Meta:
        model = DailyStats
        fields = [
            "id", "date", "emails_sent", "emails_delivered",
            "emails_opened", "unique_opens", "emails_clicked",
            "unique_clicks", "bounces", "unsubscribes", "complaints",
            "new_contacts", "contacts_unsubscribed",
            "campaigns_sent", "automation_emails_sent",
            "open_rate", "click_rate", "bounce_rate",
        ]


class CampaignClickEventSerializer(serializers.ModelSerializer):
    contact_email = serializers.CharField(
        source="campaign_email.contact.email", read_only=True,
    )

    class Meta:
        model = CampaignClickEvent
        fields = [
            "id", "campaign_email", "contact_email", "url", "link_id",
            "user_agent", "ip_address", "country", "city",
            "device_type", "browser", "os", "clicked_at",
        ]


class CampaignOpenEventSerializer(serializers.ModelSerializer):
    contact_email = serializers.CharField(
        source="campaign_email.contact.email", read_only=True,
    )

    class Meta:
        model = CampaignOpenEvent
        fields = [
            "id", "campaign_email", "contact_email",
            "user_agent", "ip_address", "country", "city",
            "device_type", "browser", "os", "opened_at",
        ]


class LinkClickSummarySerializer(serializers.ModelSerializer):
    click_rate = serializers.SerializerMethodField()

    class Meta:
        model = LinkClickSummary
        fields = [
            "id", "campaign", "url", "link_id",
            "total_clicks", "unique_clicks", "click_rate",
            "last_clicked_at",
        ]

    def get_click_rate(self, obj):
        campaign = obj.campaign
        if campaign.total_sent == 0:
            return 0
        return round((obj.unique_clicks / campaign.total_sent) * 100, 2)


class DashboardSummarySerializer(serializers.Serializer):
    """Summary stats for the main dashboard."""
    total_contacts = serializers.IntegerField()
    active_contacts = serializers.IntegerField()
    total_campaigns = serializers.IntegerField()
    campaigns_sent_this_month = serializers.IntegerField()
    emails_sent_this_month = serializers.IntegerField()
    average_open_rate = serializers.FloatField()
    average_click_rate = serializers.FloatField()
    active_automations = serializers.IntegerField()
    contacts_added_this_month = serializers.IntegerField()
    unsubscribes_this_month = serializers.IntegerField()


class DateRangeSerializer(serializers.Serializer):
    """Validate date range query params."""
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                "start_date must be before end_date."
            )
        delta = attrs["end_date"] - attrs["start_date"]
        if delta.days > 365:
            raise serializers.ValidationError(
                "Date range cannot exceed 365 days."
            )
        return attrs
