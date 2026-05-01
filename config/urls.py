"""
URL configuration for INSIS API project.

Root URL dispatcher with /api/v1/ prefix.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 routes will be added here as apps are built
    # path("api/v1/auth/", include("apps.users.urls")),
    # path("api/v1/courses/", include("apps.courses.urls")),
    # path("api/v1/enrollments/", include("apps.enrollments.urls")),
    # path("api/v1/quizzes/", include("apps.quizzes.urls")),
    # path("api/v1/companies/", include("apps.companies.urls")),
    # path("api/v1/assignments/", include("apps.assignments.urls")),
    # path("api/v1/reports/", include("apps.reports.urls")),
]
