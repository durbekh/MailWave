import logging

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    AutomationWorkflow, AutomationStep,
    AutomationEnrollment, AutomationStepLog,
)
from .serializers import (
    AutomationWorkflowListSerializer,
    AutomationWorkflowDetailSerializer,
    AutomationStepSerializer,
    AutomationEnrollmentSerializer,
    AutomationStepLogSerializer,
    EnrollContactSerializer,
)
from .services import AutomationEngine

logger = logging.getLogger(__name__)


class AutomationWorkflowViewSet(viewsets.ModelViewSet):
    """Full CRUD for automation workflows with activation controls."""

    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "trigger_type"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "total_enrolled"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return AutomationWorkflowListSerializer
        return AutomationWorkflowDetailSerializer

    def get_queryset(self):
        return AutomationWorkflow.objects.filter(
            organization=self.request.user.organization,
        ).prefetch_related("steps")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate an automation workflow."""
        workflow = self.get_object()

        if workflow.steps.count() == 0:
            return Response(
                {"error": "Workflow must have at least one step to activate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email_steps = workflow.steps.filter(step_type=AutomationStep.StepType.SEND_EMAIL)
        for step in email_steps:
            if not step.email_content and not step.email_template:
                return Response(
                    {"error": f"Step '{step}' requires email content or a template."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        workflow.status = AutomationWorkflow.Status.ACTIVE
        workflow.save(update_fields=["status"])
        logger.info("Automation %s activated by %s", workflow.id, request.user.email)
        return Response({"message": "Automation activated."})

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        """Pause an active automation."""
        workflow = self.get_object()
        if workflow.status != AutomationWorkflow.Status.ACTIVE:
            return Response(
                {"error": "Only active automations can be paused."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.status = AutomationWorkflow.Status.PAUSED
        workflow.save(update_fields=["status"])
        return Response({"message": "Automation paused."})

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """Resume a paused automation."""
        workflow = self.get_object()
        if workflow.status != AutomationWorkflow.Status.PAUSED:
            return Response(
                {"error": "Only paused automations can be resumed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        workflow.status = AutomationWorkflow.Status.ACTIVE
        workflow.save(update_fields=["status"])
        return Response({"message": "Automation resumed."})

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """Archive an automation and exit all active enrollments."""
        workflow = self.get_object()
        workflow.status = AutomationWorkflow.Status.ARCHIVED
        workflow.save(update_fields=["status"])

        active_enrollments = workflow.enrollments.filter(
            status=AutomationEnrollment.Status.ACTIVE,
        )
        count = active_enrollments.count()
        active_enrollments.update(
            status=AutomationEnrollment.Status.EXITED,
            exited_at=timezone.now(),
            exit_reason="Automation archived",
        )

        return Response({
            "message": f"Automation archived. {count} active enrollments exited.",
        })

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        """Manually enroll a contact in this automation."""
        workflow = self.get_object()

        if workflow.status != AutomationWorkflow.Status.ACTIVE:
            return Response(
                {"error": "Automation must be active to enroll contacts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = EnrollContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contact_id = serializer.validated_data["contact_id"]

        if AutomationEnrollment.objects.filter(
            workflow=workflow, contact_id=contact_id,
        ).exists():
            return Response(
                {"error": "Contact is already enrolled in this automation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        enrollment = AutomationEngine.enroll_contact(workflow, contact_id)
        return Response(
            AutomationEnrollmentSerializer(enrollment).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def enrollments(self, request, pk=None):
        """List enrollments for this automation."""
        workflow = self.get_object()
        enrollments = workflow.enrollments.select_related(
            "contact", "current_step",
        )

        enrollment_status = request.query_params.get("status")
        if enrollment_status:
            enrollments = enrollments.filter(status=enrollment_status)

        page = self.paginate_queryset(enrollments)
        if page is not None:
            serializer = AutomationEnrollmentSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AutomationEnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get automation performance stats."""
        workflow = self.get_object()

        step_stats = []
        for step in workflow.steps.all():
            step_stats.append({
                "step_id": str(step.id),
                "step_name": str(step),
                "step_type": step.step_type,
                "position": step.position,
                "total_entered": step.total_entered,
                "total_completed": step.total_completed,
                "completion_rate": (
                    round((step.total_completed / step.total_entered) * 100, 2)
                    if step.total_entered > 0 else 0
                ),
            })

        return Response({
            "total_enrolled": workflow.total_enrolled,
            "total_completed": workflow.total_completed,
            "total_exited": workflow.total_exited,
            "currently_active": workflow.currently_active,
            "conversion_rate": workflow.conversion_rate,
            "steps": step_stats,
        })


class AutomationStepViewSet(viewsets.ModelViewSet):
    """CRUD for individual automation steps."""

    serializer_class = AutomationStepSerializer

    def get_queryset(self):
        workflow_id = self.kwargs.get("workflow_pk")
        return AutomationStep.objects.filter(
            workflow_id=workflow_id,
            workflow__organization=self.request.user.organization,
        )

    def perform_create(self, serializer):
        workflow_id = self.kwargs.get("workflow_pk")
        workflow = AutomationWorkflow.objects.get(
            id=workflow_id,
            organization=self.request.user.organization,
        )
        max_position = workflow.steps.count()
        serializer.save(workflow=workflow, position=max_position)
