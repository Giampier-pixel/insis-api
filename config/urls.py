"""
URL configuration for INSIS API project.

Root URL dispatcher with /api/v1/ prefix.
"""

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/v1/auth/", include("apps.users.urls")),
    path("api/v1/", include("apps.companies.urls")),
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.enrollments.urls")),
    path("api/v1/", include("apps.quizzes.urls")),
    path("api/v1/", include("apps.assignments.urls")),
    path("api/v1/", include("apps.reports.urls")),
    # path("api/v1/quizzes/", include("apps.quizzes.urls")),
    # path("api/v1/assignments/", include("apps.assignments.urls")),
]
