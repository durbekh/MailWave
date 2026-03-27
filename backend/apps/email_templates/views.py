import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import EmailTemplate, TemplateCategory, TemplateBlock
from .serializers import (
    EmailTemplateListSerializer,
    EmailTemplateDetailSerializer,
    TemplateCategorySerializer,
    TemplateBlockSerializer,
    TemplateRenderSerializer,
    TemplateDuplicateSerializer,
)

logger = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """CRUD for email templates with builder support."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["template_type", "category", "is_starred", "is_active"]
    search_fields = ["name", "description", "subject"]
    ordering_fields = ["name", "created_at", "updated_at", "usage_count"]
    ordering = ["-updated_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return EmailTemplateListSerializer
        return EmailTemplateDetailSerializer

    def get_queryset(self):
        org = self.request.user.organization
        return EmailTemplate.objects.filter(
            organization=org, is_active=True,
        ).select_related("category", "created_by") | EmailTemplate.objects.filter(
            template_type=EmailTemplate.TemplateType.SYSTEM, is_active=True,
        ).select_related("category", "created_by")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def duplicate(self, request, pk=None):
        """Duplicate a template."""
        template = self.get_object()
        serializer = TemplateDuplicateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_template = template.duplicate(user=request.user)
        custom_name = serializer.validated_data.get("name")
        if custom_name:
            new_template.name = custom_name
            new_template.save(update_fields=["name"])

        new_template.organization = request.user.organization
        new_template.save(update_fields=["organization"])

        return Response(
            EmailTemplateDetailSerializer(new_template).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def render_preview(self, request, pk=None):
        """Render a template with sample merge data for preview."""
        template = self.get_object()
        serializer = TemplateRenderSerializer(data={
            "html_content": template.html_content,
            "merge_data": request.data.get("merge_data", {}),
        })
        serializer.is_valid(raise_exception=True)

        from utils.email_sender import EmailSender
        sender = EmailSender()

        merge_data = serializer.validated_data.get("merge_data", {})
        if not merge_data:
            merge_data = {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "company": "Acme Corp",
                "city": "San Francisco",
            }

        rendered_html = sender.personalize_content(
            template.html_content, merge_data,
        )

        return Response({
            "html": rendered_html,
            "subject": template.subject,
            "merge_tags": template.merge_tags,
        })

    @action(detail=True, methods=["post"])
    def toggle_star(self, request, pk=None):
        """Toggle the starred status of a template."""
        template = self.get_object()
        template.is_starred = not template.is_starred
        template.save(update_fields=["is_starred"])
        return Response({"is_starred": template.is_starred})

    @action(detail=False, methods=["get"])
    def starred(self, request):
        """Get all starred templates."""
        templates = self.get_queryset().filter(is_starred=True)
        serializer = EmailTemplateListSerializer(templates, many=True)
        return Response(serializer.data)


class TemplateCategoryViewSet(viewsets.ModelViewSet):
    """CRUD for template categories."""

    serializer_class = TemplateCategorySerializer
    queryset = TemplateCategory.objects.filter(is_active=True)
    filter_backends = [SearchFilter]
    search_fields = ["name"]


class TemplateBlockViewSet(viewsets.ModelViewSet):
    """CRUD for reusable template blocks."""

    serializer_class = TemplateBlockSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ["block_type"]
    search_fields = ["name"]

    def get_queryset(self):
        org = self.request.user.organization
        return TemplateBlock.objects.filter(
            organization=org,
        ) | TemplateBlock.objects.filter(is_global=True)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)
