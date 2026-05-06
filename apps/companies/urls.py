from django.urls import include, path

from rest_framework.routers import DefaultRouter

from apps.companies import views

router = DefaultRouter()
router.register("companies", views.CompanyViewSet, basename="company")
router.register("employees", views.EmployeeViewSet, basename="employee")

urlpatterns = [
    path("", include(router.urls)),
]
