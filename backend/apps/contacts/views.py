import csv
import io
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.parsers import MultiPartParser, JSONParser

from .models import Contact, ContactList, Tag, Segment
from .serializers import (
    ContactSerializer,
    ContactListSerializer,
    TagSerializer,
    SegmentSerializer,
    ContactCreateBulkSerializer,
    SegmentPreviewSerializer,
)

logger = logging.getLogger(__name__)


class ContactViewSet(viewsets.ModelViewSet):
    """CRUD operations for contacts."""

    serializer_class = ContactSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["status", "source"]
    search_fields = ["email", "first_name", "last_name", "company"]
    ordering_fields = ["email", "first_name", "created_at", "lead_score", "total_opens"]
    ordering = ["-created_at"]

    def get_queryset(self):
        org = self.request.user.organization
        qs = Contact.objects.filter(organization=org).prefetch_related("tags", "lists")

        # Filter by list
        list_id = self.request.query_params.get("list_id")
        if list_id:
            qs = qs.filter(lists__id=list_id)

        # Filter by tag
        tag_id = self.request.query_params.get("tag_id")
        if tag_id:
            qs = qs.filter(tags__id=tag_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    @action(detail=False, methods=["post"], url_path="bulk-import",
            parser_classes=[MultiPartParser, JSONParser])
    def bulk_import(self, request):
        """Bulk import contacts from JSON or CSV file."""
        org = request.user.organization

        # Handle CSV file upload
        if "file" in request.FILES:
            csv_file = request.FILES["file"]
            decoded = csv_file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(decoded))
            contacts_data = []
            for row in reader:
                contacts_data.append({
                    "email": row.get("email", "").strip().lower(),
                    "first_name": row.get("first_name", "").strip(),
                    "last_name": row.get("last_name", "").strip(),
                    "company": row.get("company", "").strip(),
                    "phone": row.get("phone", "").strip(),
                    "city": row.get("city", "").strip(),
                    "state": row.get("state", "").strip(),
                    "country": row.get("country", "").strip(),
                })
            request_data = {
                "contacts": contacts_data,
                "list_id": request.data.get("list_id"),
                "tag_ids": request.data.getlist("tag_ids", []),
                "update_existing": request.data.get("update_existing", False),
            }
        else:
            request_data = request.data

        serializer = ContactCreateBulkSerializer(data=request_data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        contacts_data = data["contacts"]
        list_id = data.get("list_id")
        tag_ids = data.get("tag_ids", [])
        update_existing = data.get("update_existing", False)

        created = 0
        updated = 0
        skipped = 0
        errors = []

        # Resolve list and tags
        contact_list = None
        if list_id:
            try:
                contact_list = ContactList.objects.get(id=list_id, organization=org)
            except ContactList.DoesNotExist:
                return Response(
                    {"error": "Contact list not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        tags = Tag.objects.filter(id__in=tag_ids, organization=org) if tag_ids else []

        with transaction.atomic():
            for i, contact_data in enumerate(contacts_data):
                email = contact_data.get("email", "").lower().strip()
                if not email:
                    skipped += 1
                    continue

                try:
                    existing = Contact.objects.filter(
                        organization=org, email=email
                    ).first()

                    if existing:
                        if update_existing:
                            for field, value in contact_data.items():
                                if field != "email" and value:
                                    setattr(existing, field, value)
                            existing.save()
                            updated += 1
                            contact = existing
                        else:
                            skipped += 1
                            contact = existing
                    else:
                        contact = Contact.objects.create(
                            organization=org,
                            email=email,
                            first_name=contact_data.get("first_name", ""),
                            last_name=contact_data.get("last_name", ""),
                            company=contact_data.get("company", ""),
                            phone=contact_data.get("phone", ""),
                            city=contact_data.get("city", ""),
                            state=contact_data.get("state", ""),
                            country=contact_data.get("country", ""),
                            source=Contact.Source.IMPORT,
                        )
                        created += 1

                    if contact_list:
                        contact.lists.add(contact_list)
                    for tag in tags:
                        contact.tags.add(tag)

                except Exception as e:
                    skipped += 1
                    errors.append({"row": i, "email": email, "error": str(e)})

        logger.info(
            "Bulk import for org %s: created=%d, updated=%d, skipped=%d",
            org.id, created, updated, skipped,
        )

        return Response({
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:50],  # Limit error details
        })

    @action(detail=True, methods=["post"])
    def unsubscribe(self, request, pk=None):
        """Unsubscribe a contact."""
        contact = self.get_object()
        contact.status = Contact.Status.UNSUBSCRIBED
        contact.unsubscribed_at = timezone.now()
        contact.save(update_fields=["status", "unsubscribed_at"])

        return Response({"message": "Contact unsubscribed successfully."})

    @action(detail=True, methods=["post"])
    def resubscribe(self, request, pk=None):
        """Resubscribe a contact."""
        contact = self.get_object()
        contact.status = Contact.Status.SUBSCRIBED
        contact.unsubscribed_at = None
        contact.save(update_fields=["status", "unsubscribed_at"])

        return Response({"message": "Contact resubscribed successfully."})


class ContactListViewSet(viewsets.ModelViewSet):
    """CRUD operations for contact lists."""

    serializer_class = ContactListSerializer
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return ContactList.objects.filter(
            organization=self.request.user.organization
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["get"])
    def contacts(self, request, pk=None):
        """Get contacts in this list."""
        contact_list = self.get_object()
        contacts = Contact.objects.filter(
            lists=contact_list, status=Contact.Status.SUBSCRIBED
        )
        page = self.paginate_queryset(contacts)
        if page is not None:
            serializer = ContactSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-contacts")
    def add_contacts(self, request, pk=None):
        """Add contacts to this list."""
        contact_list = self.get_object()
        contact_ids = request.data.get("contact_ids", [])
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            organization=request.user.organization,
        )
        contact_list.contacts.add(*contacts)
        return Response({"added": contacts.count()})

    @action(detail=True, methods=["post"], url_path="remove-contacts")
    def remove_contacts(self, request, pk=None):
        """Remove contacts from this list."""
        contact_list = self.get_object()
        contact_ids = request.data.get("contact_ids", [])
        contacts = Contact.objects.filter(
            id__in=contact_ids,
            organization=request.user.organization,
        )
        contact_list.contacts.remove(*contacts)
        return Response({"removed": contacts.count()})


class TagViewSet(viewsets.ModelViewSet):
    """CRUD operations for tags."""

    serializer_class = TagSerializer
    filter_backends = [SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        return Tag.objects.filter(organization=self.request.user.organization)

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)


class SegmentViewSet(viewsets.ModelViewSet):
    """CRUD operations for segments."""

    serializer_class = SegmentSerializer

    def get_queryset(self):
        return Segment.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related("rules")

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            created_by=self.request.user,
        )

    @action(detail=True, methods=["get"])
    def contacts(self, request, pk=None):
        """Get contacts matching this segment."""
        segment = self.get_object()
        contacts = segment.get_contacts()
        page = self.paginate_queryset(contacts)
        if page is not None:
            serializer = ContactSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def preview(self, request):
        """Preview segment results without saving."""
        serializer = SegmentPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create a temporary segment for evaluation
        temp_segment = Segment(
            organization=request.user.organization,
            match_type=serializer.validated_data["match_type"],
        )
        temp_segment.save()

        from .models import SegmentRule
        for rule_data in serializer.validated_data["rules"]:
            SegmentRule.objects.create(segment=temp_segment, **rule_data)

        count = temp_segment.contact_count
        contacts = temp_segment.get_contacts()[:10]

        # Clean up temp segment
        temp_segment.delete()

        return Response({
            "total_count": count,
            "sample_contacts": ContactSerializer(contacts, many=True).data,
        })
