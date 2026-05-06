from rest_framework import serializers

from apps.enrollments.models import Enrollment, LessonProgress


class LessonProgressSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    lesson_order = serializers.IntegerField(source="lesson.order", read_only=True)

    class Meta:
        model = LessonProgress
        fields = (
            "id",
            "lesson",
            "lesson_title",
            "lesson_order",
            "completed",
            "completed_at",
            "time_spent_seconds",
        )
        read_only_fields = ("id", "completed_at")


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    progress_pct = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student_email",
            "course",
            "course_title",
            "course_slug",
            "source",
            "enrolled_at",
            "is_active",
            "completed",
            "completed_at",
            "progress_pct",
        )
        read_only_fields = (
            "id",
            "student_email",
            "course_title",
            "course_slug",
            "source",
            "enrolled_at",
            "completed",
            "completed_at",
        )

    def get_progress_pct(self, obj) -> float | None:
        total = getattr(obj, "total_lessons", None)
        done = getattr(obj, "completed_lessons", None)
        if total is None or done is None:
            return None
        if total == 0:
            return 0
        return round((done / total) * 100, 1)


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ("course",)


class EnrollmentDetailSerializer(EnrollmentSerializer):
    lesson_progresses = LessonProgressSerializer(many=True, read_only=True)

    class Meta(EnrollmentSerializer.Meta):
        fields = EnrollmentSerializer.Meta.fields + ("lesson_progresses",)


class CompleteLessonSerializer(serializers.Serializer):
    lesson_id = serializers.IntegerField()
    time_spent_seconds = serializers.IntegerField(min_value=0, default=0)
