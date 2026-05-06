from django.urls import include, path

from rest_framework.routers import DefaultRouter

from apps.courses import views

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("tags", views.TagViewSet, basename="tag")
router.register("courses", views.CourseViewSet, basename="course")

urlpatterns = [
    path("", include(router.urls)),
]
