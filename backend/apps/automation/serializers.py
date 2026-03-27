from rest_framework import serializers
from .models import (
    AutomationWorkflow, AutomationStep,
    AutomationEnrollment, AutomationStepLog,
)


class AutomationStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationStep
        fields = [
            "id", "step_type", "name", "position",
            "email_template", "email_subject", "email_content",
            "delay_amount", "delay_unit",
            "condition_config", "yes_next_step", "no_next_step",
            "action_config", "is_active",
            "total_entered", "total_completed",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_entered", "total_completed",
            "created_at", "updated_at",
        ]


class AutomationWorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listings."""
    step_count = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AutomationWorkflow
        fields = [
            "id", "name", "description", "status", "trigger_type",
            "step_count", "total_enrolled", "total_completed",
            "currently_active", "conversion_rate",
            "created_by_name", "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name
        return ""


class AutomationWorkflowDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer with steps."""
    steps = AutomationStepSerializer(many=True, required=False)
    step_count = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()

    class Meta:
        model = AutomationWorkflow
        fields = [
            "id", "name", "description", "status", "trigger_type",
            "trigger_config", "steps", "step_count",
            "total_enrolled", "total_completed", "total_exited",
            "currently_active", "conversion_rate",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "total_enrolled", "total_completed",
            "total_exited", "currently_active",
            "created_at", "updated_at",
        ]

    def create(self, validated_data):
        steps_data = validated_data.pop("steps", [])
        workflow = AutomationWorkflow.objects.create(**validated_data)

        for i, step_data in enumerate(steps_data):
            step_data["position"] = i
            AutomationStep.objects.create(workflow=workflow, **step_data)

        return workflow

    def update(self, instance, validated_data):
        steps_data = validated_data.pop("steps", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if steps_data is not None:
            existing_step_ids = set(
                instance.steps.values_list("id", flat=True)
            )
            incoming_step_ids = set()

            for i, step_data in enumerate(steps_data):
                step_id = step_data.get("id")
                step_data["position"] = i

                if step_id and step_id in existing_step_ids:
                    step = AutomationStep.objects.get(id=step_id)
                    for attr, value in step_data.items():
                        if attr != "id":
                            setattr(step, attr, value)
                    step.save()
                    incoming_step_ids.add(step_id)
                else:
                    new_step = AutomationStep.objects.create(
                        workflow=instance, **step_data,
                    )
                    incoming_step_ids.add(new_step.id)

            # Remove steps that were deleted
            steps_to_delete = existing_step_ids - incoming_step_ids
            if steps_to_delete:
                AutomationStep.objects.filter(id__in=steps_to_delete).delete()

        return instance


class AutomationEnrollmentSerializer(serializers.ModelSerializer):
    contact_email = serializers.CharField(source="contact.email", read_only=True)
    contact_name = serializers.CharField(source="contact.full_name", read_only=True)
    current_step_name = serializers.SerializerMethodField()

    class Meta:
        model = AutomationEnrollment
        fields = [
            "id", "workflow", "contact", "contact_email", "contact_name",
            "current_step", "current_step_name", "status",
            "next_action_at", "enrolled_at", "completed_at",
            "exited_at", "exit_reason",
        ]
        read_only_fields = [
            "id", "enrolled_at", "completed_at", "exited_at",
        ]

    def get_current_step_name(self, obj):
        if obj.current_step:
            return str(obj.current_step)
        return ""


class AutomationStepLogSerializer(serializers.ModelSerializer):
    step_name = serializers.CharField(source="step.__str__", read_only=True)

    class Meta:
        model = AutomationStepLog
        fields = [
            "id", "enrollment", "step", "step_name",
            "result", "details", "error_message", "executed_at",
        ]
        read_only_fields = ["id", "executed_at"]


class EnrollContactSerializer(serializers.Serializer):
    """Serializer for manually enrolling a contact in a workflow."""
    contact_id = serializers.UUIDField()

    def validate_contact_id(self, value):
        from apps.contacts.models import Contact
        try:
            Contact.objects.get(id=value)
        except Contact.DoesNotExist:
            raise serializers.ValidationError("Contact not found.")
        return value
