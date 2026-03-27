from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedSimpleRouter

from . import views

router = DefaultRouter()
router.register("", views.AutomationWorkflowViewSet, basename="automations")

# Nested router for steps within a workflow
# URL: /api/automation/<workflow_pk>/steps/
steps_router = NestedSimpleRouter(router, "", lookup="workflow")
steps_router.register("steps", views.AutomationStepViewSet, basename="automation-steps")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(steps_router.urls)),
]
