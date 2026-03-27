from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.ContactViewSet, basename="contacts")
router.register("lists", views.ContactListViewSet, basename="contact-lists")
router.register("tags", views.TagViewSet, basename="tags")
router.register("segments", views.SegmentViewSet, basename="segments")

urlpatterns = [
    path("", include(router.urls)),
]
