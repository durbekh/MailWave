"""
Tests for the contacts app: contact management, lists, segments, bulk import.
"""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Organization, Plan
from apps.contacts.models import Contact, ContactList, Tag, Segment, SegmentRule


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class ContactTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.plan = Plan.objects.create(
            name="Free", tier=Plan.PlanTier.FREE,
            monthly_email_limit=1000, max_contacts=500,
        )
        self.organization = Organization.objects.create(
            name="Contact Test Org", slug="contact-test-org", plan=self.plan,
        )
        self.user = User.objects.create_user(
            email="contact_admin@test.com", password="ContactP@ss123!",
            first_name="Contact", last_name="Admin",
            organization=self.organization, role=User.Role.OWNER,
        )
        self.client.force_authenticate(user=self.user)


class ContactCRUDTests(ContactTestBase):
    def test_create_contact(self):
        data = {
            "email": "subscriber@example.com",
            "first_name": "Jane",
            "last_name": "Doe",
            "company": "Acme Corp",
        }
        response = self.client.post("/api/contacts/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["email"], "subscriber@example.com")

    def test_create_duplicate_email_fails(self):
        Contact.objects.create(
            organization=self.organization, email="dup@example.com",
        )
        data = {"email": "dup@example.com", "first_name": "Dup"}
        response = self.client.post("/api/contacts/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_contacts_with_search(self):
        Contact.objects.create(
            organization=self.organization, email="alice@example.com",
            first_name="Alice",
        )
        Contact.objects.create(
            organization=self.organization, email="bob@example.com",
            first_name="Bob",
        )
        response = self.client.get("/api/contacts/?search=alice")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["first_name"], "Alice")

    def test_unsubscribe_contact(self):
        contact = Contact.objects.create(
            organization=self.organization, email="unsub@example.com",
        )
        response = self.client.post(f"/api/contacts/{contact.id}/unsubscribe/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contact.refresh_from_db()
        self.assertEqual(contact.status, Contact.Status.UNSUBSCRIBED)
        self.assertIsNotNone(contact.unsubscribed_at)

    def test_resubscribe_contact(self):
        contact = Contact.objects.create(
            organization=self.organization, email="resub@example.com",
            status=Contact.Status.UNSUBSCRIBED,
        )
        response = self.client.post(f"/api/contacts/{contact.id}/resubscribe/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contact.refresh_from_db()
        self.assertEqual(contact.status, Contact.Status.SUBSCRIBED)


class ContactListTests(ContactTestBase):
    def test_create_contact_list(self):
        data = {"name": "Newsletter Subscribers", "description": "Main list"}
        response = self.client.post("/api/contacts/lists/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_add_contacts_to_list(self):
        contact_list = ContactList.objects.create(
            organization=self.organization, name="VIP",
            created_by=self.user,
        )
        c1 = Contact.objects.create(
            organization=self.organization, email="c1@example.com",
        )
        c2 = Contact.objects.create(
            organization=self.organization, email="c2@example.com",
        )
        data = {"contact_ids": [str(c1.id), str(c2.id)]}
        response = self.client.post(
            f"/api/contacts/lists/{contact_list.id}/add-contacts/",
            data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["added"], 2)


class BulkImportTests(ContactTestBase):
    def test_bulk_import_json(self):
        data = {
            "contacts": [
                {"email": "import1@example.com", "first_name": "Import1"},
                {"email": "import2@example.com", "first_name": "Import2"},
                {"email": "import3@example.com", "first_name": "Import3"},
            ],
            "update_existing": False,
        }
        response = self.client.post(
            "/api/contacts/bulk-import/", data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["created"], 3)
        self.assertEqual(response.data["skipped"], 0)

    def test_bulk_import_skips_duplicates(self):
        Contact.objects.create(
            organization=self.organization, email="existing@example.com",
        )
        data = {
            "contacts": [
                {"email": "existing@example.com", "first_name": "Existing"},
                {"email": "new@example.com", "first_name": "New"},
            ],
            "update_existing": False,
        }
        response = self.client.post(
            "/api/contacts/bulk-import/", data, format="json",
        )
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["skipped"], 1)


class SegmentTests(ContactTestBase):
    def test_create_segment_with_rules(self):
        data = {
            "name": "High Engagement",
            "match_type": "all",
            "rules": [
                {"field": "total_opens", "operator": "greater_than", "value": "10"},
                {"field": "country", "operator": "equals", "value": "US"},
            ],
        }
        response = self.client.post(
            "/api/contacts/segments/", data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["rules"]), 2)

    def test_segment_rule_evaluation(self):
        segment = Segment.objects.create(
            organization=self.organization, name="Active",
            match_type=Segment.MatchType.ALL,
            created_by=self.user,
        )
        SegmentRule.objects.create(
            segment=segment, field="country",
            operator=SegmentRule.Operator.EQUALS, value="US",
        )

        Contact.objects.create(
            organization=self.organization, email="us@example.com",
            country="US",
        )
        Contact.objects.create(
            organization=self.organization, email="uk@example.com",
            country="UK",
        )

        contacts = segment.get_contacts()
        self.assertEqual(contacts.count(), 1)
        self.assertEqual(contacts.first().email, "us@example.com")


class ContactModelTests(TestCase):
    def test_merge_dict(self):
        contact = Contact(
            email="test@example.com", first_name="John", last_name="Doe",
            company="Acme", city="NYC", state="NY", country="US",
            custom_fields={"role": "dev"},
        )
        merge = contact.to_merge_dict()
        self.assertEqual(merge["email"], "test@example.com")
        self.assertEqual(merge["full_name"], "John Doe")
        self.assertEqual(merge["custom_fields"]["role"], "dev")

    def test_engagement_rate(self):
        contact = Contact(total_emails_received=100, total_opens=25)
        self.assertEqual(contact.engagement_rate, 25.0)

    def test_engagement_rate_zero_emails(self):
        contact = Contact(total_emails_received=0, total_opens=0)
        self.assertEqual(contact.engagement_rate, 0)
