from django.utils.text import slugify

from rest_framework import serializers

from apps.courses.models import Course


class InstructorBasicSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class CourseListSerializer(serializers.ModelSerializer):
    instructor = InstructorBasicSerializer(read_only=True)
    quiz_count = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "description",
            "is_published",
            "instructor",
            "quiz_count",
            "enrolled_count",
            "is_enrolled",
            "created_at",
        )

    def get_quiz_count(self, obj) -> int:
        return getattr(obj, "quiz_count", obj.quizzes.filter(is_active=True).count())

    def get_enrolled_count(self, obj) -> int:
        return getattr(obj, "enrolled_count", 0)

    def get_is_enrolled(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.enrollments.filter(
            student=request.user, is_active=True
        ).exists()


class CourseDetailSerializer(CourseListSerializer):
    quizzes = serializers.SerializerMethodField()

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + ("quizzes",)

    def get_quizzes(self, obj) -> list[dict]:
        qs = obj.quizzes.filter(is_active=True).order_by("id")
        return [{"id": q.id, "title": q.title} for q in qs]


class CourseWriteSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=255, required=False, allow_blank=True, default="")

    class Meta:
        model = Course
        fields = ("title", "slug", "description", "instructor", "is_published")

    def validate(self, data):
        if not data.get("slug") and data.get("title"):
            data["slug"] = slugify(data["title"])
        return data
