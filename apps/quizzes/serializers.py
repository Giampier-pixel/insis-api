from rest_framework import serializers

from apps.quizzes.models import Attempt, AttemptAnswer, Option, Question, Quiz


class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("id", "text", "order", "is_correct")


class OptionPublicSerializer(serializers.ModelSerializer):
    """Strips is_correct for students."""

    class Meta:
        model = Option
        fields = ("id", "text", "order")


class OptionWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ("text", "is_correct", "order")


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "type", "order", "points", "options")


class QuestionPublicSerializer(serializers.ModelSerializer):
    options = OptionPublicSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ("id", "text", "type", "order", "points", "options")


class QuestionWriteSerializer(serializers.ModelSerializer):
    options = OptionWriteSerializer(many=True)

    class Meta:
        model = Question
        fields = ("text", "type", "order", "points", "options")

    def validate_options(self, options):
        if len(options) < 2:
            raise serializers.ValidationError("At least 2 options required.")
        if not any(o.get("is_correct") for o in options):
            raise serializers.ValidationError("At least 1 correct option required.")
        return options

    def create(self, validated_data):
        options_data = validated_data.pop("options")
        question = Question.objects.create(**validated_data)
        for opt in options_data:
            Option.objects.create(question=question, **opt)
        return question

    def update(self, instance, validated_data):
        options_data = validated_data.pop("options", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if options_data is not None:
            instance.options.all().delete()
            for opt in options_data:
                Option.objects.create(question=instance, **opt)
        return instance


class QuizListSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = (
            "id",
            "course",
            "lesson",
            "title",
            "description",
            "time_limit_minutes",
            "max_attempts",
            "passing_score",
            "is_active",
            "question_count",
        )

    def get_question_count(self, obj) -> int:
        return getattr(obj, "question_count", obj.questions.count())


class QuizDetailSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = (
            "id",
            "course",
            "lesson",
            "title",
            "description",
            "time_limit_minutes",
            "max_attempts",
            "passing_score",
            "is_active",
            "questions",
        )

    def get_questions(self, obj):
        request = self.context.get("request")
        show_answers = (
            request
            and request.user.is_authenticated
            and request.user.role in ("INSTRUCTOR", "ADMIN")
        )
        qs = obj.questions.prefetch_related("options").order_by("order")
        serializer = QuestionSerializer if show_answers else QuestionPublicSerializer
        return serializer(qs, many=True).data


class QuizWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = (
            "course",
            "lesson",
            "title",
            "description",
            "time_limit_minutes",
            "max_attempts",
            "passing_score",
            "is_active",
        )

    def validate(self, data):
        lesson = data.get("lesson") or getattr(self.instance, "lesson", None)
        course = data.get("course") or getattr(self.instance, "course", None)
        if lesson and course and lesson.course_id != course.pk:
            raise serializers.ValidationError(
                {"lesson": "Lesson does not belong to the selected course."}
            )
        return data

    def validate_passing_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "Passing score must be between 0 and 100."
            )
        return value


class AttemptSerializer(serializers.ModelSerializer):
    quiz_title = serializers.CharField(source="quiz.title", read_only=True)

    class Meta:
        model = Attempt
        fields = (
            "id",
            "quiz",
            "quiz_title",
            "attempt_number",
            "started_at",
            "finished_at",
            "score",
            "passed",
        )
        read_only_fields = fields


class AttemptAnswerSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source="question.text", read_only=True)
    question_type = serializers.CharField(source="question.type", read_only=True)
    selected_option_ids = serializers.SerializerMethodField()
    correct_option_ids = serializers.SerializerMethodField()

    class Meta:
        model = AttemptAnswer
        fields = (
            "id",
            "question",
            "question_text",
            "question_type",
            "is_correct",
            "points_earned",
            "selected_option_ids",
            "correct_option_ids",
        )

    def get_selected_option_ids(self, obj) -> list[int]:
        return list(obj.selected_options.values_list("id", flat=True))

    def get_correct_option_ids(self, obj) -> list[int]:
        return list(
            obj.question.options.filter(is_correct=True).values_list("id", flat=True)
        )


class AttemptDetailSerializer(AttemptSerializer):
    answers = AttemptAnswerSerializer(many=True, read_only=True)

    class Meta(AttemptSerializer.Meta):
        fields = AttemptSerializer.Meta.fields + ("answers",)


class SubmittedAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=True
    )


class SubmitSerializer(serializers.Serializer):
    answers = SubmittedAnswerSerializer(many=True)
