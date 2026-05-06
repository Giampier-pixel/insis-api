from rest_framework.routers import DefaultRouter

from apps.assignments.views import CourseAssignmentViewSet

router = DefaultRouter()
router.register("assignments", CourseAssignmentViewSet, basename="assignment")

urlpatterns = router.urls
