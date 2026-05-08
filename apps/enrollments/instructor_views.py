from django.db.models import Count, Q

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.enrollments.models import Enrollment
from apps.quizzes.models import Attempt
from apps.users.models import Roles
from apps.users.permissions import IsInstructor


class InstructorStudentsView(APIView):
    permission_classes = [IsInstructor]

    def get(self, request):
        course_id = request.query_params.get("course")

        enrollments = (
            Enrollment.objects.select_related("student", "course")
            .filter(course__instructor=request.user, is_active=True)
        )
        if course_id:
            enrollments = enrollments.filter(course_id=course_id)

        results = []
        for enrollment in enrollments:
            total_quizzes = enrollment.course.quizzes.filter(is_active=True).count()
            quizzes_completed = (
                Attempt.objects.filter(
                    quiz__course=enrollment.course,
                    student=enrollment.student,
                    passed=True,
                    finished_at__isnull=False,
                )
                .values("quiz_id")
                .distinct()
                .count()
            )
            results.append(
                {
                    "student_id": enrollment.student.id,
                    "student_name": enrollment.student.full_name,
                    "student_email": enrollment.student.email,
                    "course_id": enrollment.course.id,
                    "course_title": enrollment.course.title,
                    "quizzes_completed": quizzes_completed,
                    "total_quizzes": total_quizzes,
                    "enrolled_at": enrollment.enrolled_at,
                }
            )

        return Response(results)
