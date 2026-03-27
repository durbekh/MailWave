import logging

from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import User, Organization, Plan
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    OrganizationSerializer,
    PlanSerializer,
    InviteMemberSerializer,
)

logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    """Register a new user and organization."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(generics.GenericAPIView):
    """Login and obtain JWT tokens."""

    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        tokens = serializer.get_tokens(user)

        # Update last login IP
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")

        user.last_login_ip = ip
        user.save(update_fields=["last_login_ip"])

        logger.info("User logged in: %s from %s", user.email, ip)

        return Response({
            "user": UserSerializer(user).data,
            "tokens": tokens,
        })


class MeView(generics.RetrieveUpdateAPIView):
    """Get or update current user profile."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Change user password."""

    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class OrganizationViewSet(viewsets.ModelViewSet):
    """Manage organization settings."""

    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(
            id=self.request.user.organization_id
        )

    def get_object(self):
        return self.request.user.organization

    @action(detail=False, methods=["get"])
    def current(self, request):
        """Get current user's organization."""
        org = request.user.organization
        if not org:
            return Response(
                {"error": "No organization found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrganizationSerializer(org).data)

    @action(detail=False, methods=["get"])
    def members(self, request):
        """List organization members."""
        org = request.user.organization
        if not org:
            return Response(
                {"error": "No organization found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        members = User.objects.filter(organization=org)
        return Response(UserSerializer(members, many=True).data)

    @action(detail=False, methods=["post"])
    def invite(self, request):
        """Invite a new member to the organization."""
        if not request.user.has_org_permission(User.Role.ADMIN):
            return Response(
                {"error": "You must be an admin to invite members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InviteMemberSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        import uuid

        temp_password = str(uuid.uuid4())[:12]
        user = User.objects.create_user(
            email=data["email"],
            password=temp_password,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            organization=request.user.organization,
            role=data["role"],
        )

        # In production, send an invitation email here
        logger.info(
            "User %s invited %s to organization %s",
            request.user.email, data["email"], request.user.organization.name,
        )

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["delete"], url_path="members/(?P<user_id>[^/.]+)")
    def remove_member(self, request, user_id=None):
        """Remove a member from the organization."""
        if not request.user.has_org_permission(User.Role.ADMIN):
            return Response(
                {"error": "You must be an admin to remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            member = User.objects.get(
                id=user_id, organization=request.user.organization
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Member not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if member.role == User.Role.OWNER:
            return Response(
                {"error": "Cannot remove the organization owner."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member.organization = None
        member.save(update_fields=["organization"])

        return Response(status=status.HTTP_204_NO_CONTENT)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    """List available plans."""

    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [permissions.AllowAny]
