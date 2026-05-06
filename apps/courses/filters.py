import django_filters

from apps.courses.models import Course, Tag


class CourseFilter(django_filters.FilterSet):
    category = django_filters.NumberFilter(field_name="category_id")
    level = django_filters.ChoiceFilter(choices=Course.Level.choices)
    min_price = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    tag = django_filters.ModelMultipleChoiceFilter(
        field_name="tags", queryset=Tag.objects.all()
    )
    is_free = django_filters.BooleanFilter(method="filter_free")

    class Meta:
        model = Course
        fields = ["category", "level", "language"]

    def filter_free(self, queryset, name, value):
        if value:
            return queryset.filter(price=0)
        return queryset.exclude(price=0)
