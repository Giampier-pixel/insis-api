from django.utils import timezone

from apps.quizzes.models import AttemptAnswer, Question


def grade_attempt(attempt, submitted_answers):
    """
    submitted_answers: [{"question_id": int, "selected_option_ids": [int, ...]}, ...]
    Grades every answer, persists AttemptAnswer rows, and closes the attempt.
    """
    total_points = 0
    earned_points = 0

    for answer in submitted_answers:
        question = Question.objects.prefetch_related("options").get(
            id=answer["question_id"], quiz=attempt.quiz
        )
        correct_ids = set(
            question.options.filter(is_correct=True).values_list("id", flat=True)
        )
        selected_ids = set(answer.get("selected_option_ids", []))
        is_correct = correct_ids == selected_ids
        pts_earned = question.points if is_correct else 0

        total_points += question.points
        earned_points += pts_earned

        aa = AttemptAnswer.objects.create(
            attempt=attempt,
            question=question,
            is_correct=is_correct,
            points_earned=pts_earned,
        )
        # Only allow option IDs that actually belong to this question (security)
        valid_ids = question.options.filter(id__in=selected_ids).values_list(
            "id", flat=True
        )
        aa.selected_options.set(valid_ids)

    score = round((earned_points / total_points * 100), 2) if total_points > 0 else 0
    attempt.score = score
    attempt.passed = score >= float(attempt.quiz.passing_score)
    attempt.finished_at = timezone.now()
    attempt.save(update_fields=["score", "passed", "finished_at"])

    return attempt
