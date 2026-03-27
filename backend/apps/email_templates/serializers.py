from rest_framework import serializers
from .models import EmailTemplate, TemplateCategory, TemplateBlock


class TemplateCategorySerializer(serializers.ModelSerializer):
    template_count = serializers.SerializerMethodField()

    class Meta:
        model = TemplateCategory
        fields = [
            "id", "name", "slug", "description", "icon",
            "sort_order", "template_count", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_template_count(self, obj):
        return obj.templates.filter(is_active=True).count()


class TemplateBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateBlock
        fields = [
            "id", "name", "block_type", "html_content",
            "json_config", "is_global", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EmailTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template listings."""
    category_name = serializers.CharField(source="category.name", read_only=True, default="")
    created_by_name = serializers.SerializerMethodField()
    merge_tags = serializers.ReadOnlyField()

    class Meta:
        model = EmailTemplate
        fields = [
            "id", "name", "description", "subject", "template_type",
            "category", "category_name", "thumbnail", "is_active",
            "is_starred", "usage_count", "created_by_name",
            "merge_tags", "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
        return ""


class EmailTemplateDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for template editing."""
    category_detail = TemplateCategorySerializer(source="category", read_only=True)
    merge_tags = serializers.ReadOnlyField()

    class Meta:
        model = EmailTemplate
        fields = [
            "id", "name", "description", "subject", "preview_text",
            "html_content", "json_content", "template_type",
            "category", "category_detail", "thumbnail",
            "is_active", "is_starred", "usage_count",
            "merge_tags", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "usage_count", "created_at", "updated_at"]

    def validate_json_content(self, value):
        """Validate the builder JSON structure."""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError(
                "json_content must be a valid JSON object."
            )
        if value:
            if "blocks" not in value and "rows" not in value:
                raise serializers.ValidationError(
                    "json_content must contain 'blocks' or 'rows' key."
                )
        return value


class TemplateRenderSerializer(serializers.Serializer):
    """Serialize data for rendering a template preview."""
    html_content = serializers.CharField(required=False)
    json_content = serializers.JSONField(required=False)
    merge_data = serializers.DictField(required=False, default=dict)

    def validate(self, attrs):
        if not attrs.get("html_content") and not attrs.get("json_content"):
            raise serializers.ValidationError(
                "Either html_content or json_content is required."
            )
        return attrs


class TemplateDuplicateSerializer(serializers.Serializer):
    """Serializer for duplicating a template."""
    name = serializers.CharField(max_length=255, required=False)
