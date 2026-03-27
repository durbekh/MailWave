from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="analytics-dashboard"),
    path("daily/", views.DailyStatsView.as_view(), name="analytics-daily"),
    path(
        "campaigns/<uuid:campaign_id>/",
        views.CampaignAnalyticsView.as_view(),
        name="analytics-campaign",
    ),
    # Tracking endpoints (public, no auth required)
    path("t/open/", views.track_open, name="track-open"),
    path("t/click/", views.track_click, name="track-click"),
    path(
        "unsubscribe/<uuid:token>/",
        views.unsubscribe_view,
        name="unsubscribe",
    ),
]
