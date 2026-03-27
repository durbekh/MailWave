from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("", views.EmailTemplateViewSet, basename="templates")
router.register("categories", views.TemplateCategoryViewSet, basename="template-categories")
router.register("blocks", views.TemplateBlockViewSet, basename="template-blocks")

urlpatterns = [
    path("", include(router.urls)),
]
