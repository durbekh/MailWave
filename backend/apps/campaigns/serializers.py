from rest_framework import serializers
from apps.contacts.serializers import ContactListSerializer, SegmentSerializer
from .models import Campaign, CampaignEmail, ABTest, CampaignSchedule


class CampaignScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignSchedule
        fields = [
            "id", "schedule_type", "scheduled_at", "timezone",
            "send_in_recipient_timezone", "batch_size", "batch_delay_seconds",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ABTestSerializer(serializers.ModelSerializer):
    variant_a_open_rate = serializers.ReadOnlyField()
    variant_b_open_rate = serializers.ReadOnlyField()
    variant_a_click_rate = serializers.ReadOnlyField()
    variant_b_click_rate = serializers.ReadOnlyField()

    class Meta:
        model = ABTest
        fields = [
            "id", "test_variable", "variant_a_subject", "variant_b_subject",
            "variant_a_content", "variant_b_content",
            "variant_a_from_name", "variant_b_from_name",
            "test_percentage", "winner_criteria", "test_duration_hours",
            "winner_variant", "winner_selected_at",
            "variant_a_sent", "variant_a_opens", "variant_a_clicks",
            "variant_b_sent", "variant_b_opens", "variant_b_clicks",
            "variant_a_open_rate", "variant_b_open_rate",
            "variant_a_click_rate", "variant_b_click_rate",
            "created_at",
        ]
        read_only_fields = [
            "id", "winner_variant", "winner_selected_at",
            "variant_a_sent", "variant_a_opens", "variant_a_clicks",
            "variant_b_sent", "variant_b_opens", "variant_b_clicks",
            "created_at",
        ]


class CampaignEmailSerializer(serializers.ModelSerializer):
    contact_email = serializers.CharField(source="contact.email", read_only=True)
    contact_name = serializers.CharField(source="contact.full_name", read_only=True)

    class Meta:
        model = CampaignEmail
        fields = [
            "id", "contact", "contact_email", "contact_name",
            "ab_variant", "status", "subject_used",
            "sent_at", "delivered_at", "opened_at", "clicked_at",
            "bounced_at", "bounce_reason", "open_count", "click_count",
            "error_message", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CampaignListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for campaign listings."""
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    bounce_rate = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=""
    )

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "subject", "status", "campaign_type",
            "total_recipients", "total_sent", "unique_opens", "unique_clicks",
            "total_bounces", "total_unsubscribes", "open_rate", "click_rate",
            "bounce_rate", "sent_at", "created_by_name",
            "created_at", "updated_at",
        ]


class CampaignDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for campaign CRUD."""
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    bounce_rate = serializers.ReadOnlyField()
    unsubscribe_rate = serializers.ReadOnlyField()
    schedule = CampaignScheduleSerializer(required=False)
    ab_test = ABTestSerializer(required=False)
    contact_lists_detail = ContactListSerializer(
        source="contact_lists", many=True, read_only=True
    )
    segments_detail = SegmentSerializer(
        source="segments", many=True, read_only=True
    )
    contact_list_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="contact_lists", write_only=True, required=False,
        queryset=None,
    )
    segment_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="segments", write_only=True, required=False,
        queryset=None,
    )
    exclude_list_ids = serializers.PrimaryKeyRelatedField(
        many=True, source="exclude_lists", write_only=True, required=False,
        queryset=None,
    )

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "subject", "preview_text", "from_name", "from_email",
            "reply_to", "html_content", "plain_text_content", "template",
            "status", "campaign_type",
            "contact_lists_detail", "segments_detail",
            "contact_list_ids", "segment_ids", "exclude_list_ids",
            "track_opens", "track_clicks",
            "total_recipients", "total_sent", "total_delivered",
            "total_opens", "unique_opens", "total_clicks", "unique_clicks",
            "total_bounces", "total_unsubscribes", "total_complaints",
            "open_rate", "click_rate", "bounce_rate", "unsubscribe_rate",
            "schedule", "ab_test",
            "sent_at", "completed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_recipients", "total_sent", "total_delivered",
            "total_opens", "unique_opens", "total_clicks", "unique_clicks",
            "total_bounces", "total_unsubscribes", "total_complaints",
            "sent_at", "completed_at", "created_at", "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request.user, "organization"):
            org = request.user.organization
            from apps.contacts.models import ContactList, Segment
            self.fields["contact_list_ids"].child_relation.queryset = (
                ContactList.objects.filter(organization=org)
            )
            self.fields["segment_ids"].child_relation.queryset = (
                Segment.objects.filter(organization=org)
            )
            self.fields["exclude_list_ids"].child_relation.queryset = (
                ContactList.objects.filter(organization=org)
            )

    def create(self, validated_data):
        schedule_data = validated_data.pop("schedule", None)
        ab_test_data = validated_data.pop("ab_test", None)
        contact_lists = validated_data.pop("contact_lists", [])
        segments = validated_data.pop("segments", [])
        exclude_lists = validated_data.pop("exclude_lists", [])

        campaign = Campaign.objects.create(**validated_data)

        if contact_lists:
            campaign.contact_lists.set(contact_lists)
        if segments:
            campaign.segments.set(segments)
        if exclude_lists:
            campaign.exclude_lists.set(exclude_lists)

        if schedule_data:
            CampaignSchedule.objects.create(campaign=campaign, **schedule_data)

        if ab_test_data:
            ABTest.objects.create(campaign=campaign, **ab_test_data)

        return campaign

    def update(self, instance, validated_data):
        schedule_data = validated_data.pop("schedule", None)
        ab_test_data = validated_data.pop("ab_test", None)
        contact_lists = validated_data.pop("contact_lists", None)
        segments = validated_data.pop("segments", None)
        exclude_lists = validated_data.pop("exclude_lists", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if contact_lists is not None:
            instance.contact_lists.set(contact_lists)
        if segments is not None:
            instance.segments.set(segments)
        if exclude_lists is not None:
            instance.exclude_lists.set(exclude_lists)

        if schedule_data:
            CampaignSchedule.objects.update_or_create(
                campaign=instance, defaults=schedule_data
            )

        if ab_test_data:
            ABTest.objects.update_or_create(
                campaign=instance, defaults=ab_test_data
            )

        return instance


class CampaignSendSerializer(serializers.Serializer):
    """Serializer for sending a campaign."""
    send_immediately = serializers.BooleanField(default=True)
    scheduled_at = serializers.DateTimeField(required=False)
    test_email = serializers.EmailField(required=False)
