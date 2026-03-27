from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Organization, Plan


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id", "name", "tier", "monthly_email_limit", "max_contacts",
            "max_campaigns_per_month", "max_automation_sequences",
            "ab_testing_enabled", "advanced_analytics", "custom_templates",
            "priority_support", "price_monthly", "price_yearly", "is_active",
        ]


class OrganizationSerializer(serializers.ModelSerializer):
    plan_details = PlanSerializer(source="plan", read_only=True)
    remaining_emails = serializers.ReadOnlyField()
    email_limit_reached = serializers.ReadOnlyField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id", "name", "slug", "plan", "plan_details", "website", "logo",
            "default_from_email", "default_from_name", "default_reply_to",
            "address_line1", "address_line2", "city", "state", "postal_code",
            "country", "emails_sent_this_month", "remaining_emails",
            "email_limit_reached", "member_count", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "emails_sent_this_month", "created_at", "updated_at"]

    def get_member_count(self, obj):
        return obj.members.count()


class UserSerializer(serializers.ModelSerializer):
    organization_details = OrganizationSerializer(source="organization", read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "organization", "organization_details", "role", "phone",
            "avatar", "timezone", "email_verified", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "email_verified", "is_active", "created_at", "updated_at",
        ]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    organization_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        org_name = validated_data.pop("organization_name")

        # Create default free plan if it doesn't exist
        free_plan, _ = Plan.objects.get_or_create(
            tier=Plan.PlanTier.FREE,
            defaults={
                "name": "Free",
                "monthly_email_limit": 1000,
                "max_contacts": 500,
                "max_campaigns_per_month": 10,
                "max_automation_sequences": 3,
            },
        )

        # Create organization
        from django.utils.text import slugify
        slug = slugify(org_name)
        counter = 1
        base_slug = slug
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        organization = Organization.objects.create(
            name=org_name,
            slug=slug,
            plan=free_plan,
        )

        # Create user as owner
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            organization=organization,
            role=User.Role.OWNER,
        )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower()
        password = attrs.get("password")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError(
                "Invalid email or password."
            )
        if not user.is_active:
            raise serializers.ValidationError(
                "This account has been deactivated."
            )

        attrs["user"] = user
        return attrs

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Passwords do not match."}
            )
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class InviteMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.EDITOR)
    first_name = serializers.CharField(max_length=150, required=False, default="")
    last_name = serializers.CharField(max_length=150, required=False, default="")

    def validate_email(self, value):
        user = self.context["request"].user
        if User.objects.filter(
            email=value, organization=user.organization
        ).exists():
            raise serializers.ValidationError(
                "A user with this email is already in your organization."
            )
        return value.lower()
