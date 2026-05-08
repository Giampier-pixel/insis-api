from django.urls import include, path

from rest_framework.routers import DefaultRouter

from apps.enrollments.views import CertificateViewSet, EnrollmentViewSet
from apps.enrollments import instructor_views

router = DefaultRouter()
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("certificates", CertificateViewSet, basename="certificate")

urlpatterns = [
    path("", include(router.urls)),
    path("instructor/students/", instructor_views.InstructorStudentsView.as_view(), name="instructor-students"),
]
