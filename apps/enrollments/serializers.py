from rest_framework import serializers

from apps.enrollments.models import Certificate, Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)
    student_email = serializers.EmailField(source="student.email", read_only=True)
    quiz_progress = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = (
            "id",
            "student_email",
            "course",
            "course_title",
            "course_slug",
            "enrolled_at",
            "is_active",
            "completed",
            "completed_at",
            "quiz_progress",
        )
        read_only_fields = (
            "id",
            "student_email",
            "course_title",
            "course_slug",
            "enrolled_at",
            "completed",
            "completed_at",
        )

    def get_quiz_progress(self, obj) -> dict:
        from apps.quizzes.models import Attempt, Quiz

        total = Quiz.objects.filter(course=obj.course, is_active=True).count()
        passed = (
            Attempt.objects.filter(
                quiz__course=obj.course,
                student=obj.student,
                passed=True,
                finished_at__isnull=False,
            )
            .values("quiz_id")
            .distinct()
            .count()
        )
        return {"total": total, "passed": passed}


class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ("course",)


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    course_slug = serializers.SlugField(source="course.slug", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = (
            "id",
            "course_title",
            "course_slug",
            "is_ready",
            "generated_at",
            "download_url",
        )

    def get_download_url(self, obj) -> str | None:
        if not obj.is_ready or not obj.pdf_file:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(f"/api/v1/certificates/{obj.id}/download/")
        return None
