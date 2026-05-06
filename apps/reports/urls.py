from rest_framework.routers import DefaultRouter

from apps.reports.views import ReportExportJobViewSet, ReportsViewSet

router = DefaultRouter()
router.register("reports/exports", ReportExportJobViewSet, basename="report-export")
router.register("reports", ReportsViewSet, basename="report")

urlpatterns = router.urls
