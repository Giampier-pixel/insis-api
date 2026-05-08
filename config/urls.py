"""URL configuration for INSIS API project."""

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from django.conf import settings
from django.conf.urls.static import static
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
    path("api/v1/", include("apps.courses.urls")),
    path("api/v1/", include("apps.enrollments.urls")),
    path("api/v1/", include("apps.quizzes.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
