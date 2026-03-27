from rest_framework import serializers
from .models import Contact, ContactList, Tag, Segment, SegmentRule


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]


class ContactListSerializer(serializers.ModelSerializer):
    contact_count = serializers.ReadOnlyField()
    unsubscribed_count = serializers.ReadOnlyField()

    class Meta:
        model = ContactList
        fields = [
            "id", "name", "description", "is_default", "double_optin",
            "contact_count", "unsubscribed_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ContactSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    engagement_rate = serializers.ReadOnlyField()
    tags_detail = TagSerializer(source="tags", many=True, read_only=True)
    lists_detail = ContactListSerializer(source="lists", many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(),
        source="tags", write_only=True, required=False,
    )
    list_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ContactList.objects.all(),
        source="lists", write_only=True, required=False,
    )

    class Meta:
        model = Contact
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "company", "phone", "city", "state", "country", "postal_code",
            "custom_fields", "status", "source", "lead_score",
            "tags_detail", "lists_detail", "tag_ids", "list_ids",
            "engagement_rate", "total_emails_received", "total_opens",
            "total_clicks", "last_emailed_at", "last_opened_at",
            "last_clicked_at", "subscribed_at", "unsubscribed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "lead_score", "total_emails_received", "total_opens",
            "total_clicks", "last_emailed_at", "last_opened_at",
            "last_clicked_at", "subscribed_at", "unsubscribed_at",
            "created_at", "updated_at",
        ]

    def validate_email(self, value):
        org = self.context["request"].user.organization
        qs = Contact.objects.filter(organization=org, email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A contact with this email already exists."
            )
        return value.lower()


class ContactCreateBulkSerializer(serializers.Serializer):
    """Bulk import contacts."""
    contacts = serializers.ListField(
        child=serializers.DictField(), min_length=1, max_length=10000,
    )
    list_id = serializers.UUIDField(required=False)
    tag_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list,
    )
    update_existing = serializers.BooleanField(default=False)


class SegmentRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SegmentRule
        fields = ["id", "field", "operator", "value", "created_at"]
        read_only_fields = ["id", "created_at"]


class SegmentSerializer(serializers.ModelSerializer):
    rules = SegmentRuleSerializer(many=True)
    contact_count = serializers.ReadOnlyField()

    class Meta:
        model = Segment
        fields = [
            "id", "name", "description", "match_type", "rules",
            "contact_count", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        rules_data = validated_data.pop("rules", [])
        segment = Segment.objects.create(**validated_data)
        for rule_data in rules_data:
            SegmentRule.objects.create(segment=segment, **rule_data)
        return segment

    def update(self, instance, validated_data):
        rules_data = validated_data.pop("rules", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if rules_data is not None:
            instance.rules.all().delete()
            for rule_data in rules_data:
                SegmentRule.objects.create(segment=instance, **rule_data)

        return instance


class SegmentPreviewSerializer(serializers.Serializer):
    """Preview segment results without saving."""
    match_type = serializers.ChoiceField(choices=Segment.MatchType.choices)
    rules = SegmentRuleSerializer(many=True)
