from django.utils.text import slugify

from rest_framework import serializers

from apps.courses.models import Category, Course, CourseReview, Lesson, Tag


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "icon", "description", "is_active")
        read_only_fields = ("id", "slug")

    def validate_name(self, value):
        return value.strip()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = ("id", "slug")


class InstructorBasicSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = (
            "id",
            "title",
            "content",
            "video_url",
            "order",
            "duration_minutes",
            "is_free",
            "is_published",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CourseReviewSerializer(serializers.ModelSerializer):
    student_email = serializers.EmailField(source="student.email", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = CourseReview
        fields = (
            "id",
            "enrollment",
            "student_email",
            "student_name",
            "rating",
            "comment",
            "created_at",
        )
        read_only_fields = (
            "id",
            "enrollment",
            "student_email",
            "student_name",
            "created_at",
        )


class CourseListSerializer(serializers.ModelSerializer):
    instructor = InstructorBasicSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    avg_rating = serializers.SerializerMethodField()
    lesson_count = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = (
            "id",
            "title",
            "slug",
            "thumbnail",
            "price",
            "level",
            "language",
            "is_published",
            "instructor",
            "category",
            "tags",
            "avg_rating",
            "lesson_count",
            "review_count",
            "enrolled_count",
            "created_at",
        )

    def get_avg_rating(self, obj) -> float | None:
        val = getattr(obj, "avg_rating", None)
        return round(val, 2) if val is not None else None

    def get_lesson_count(self, obj) -> int:
        return getattr(obj, "lesson_count", 0)

    def get_review_count(self, obj) -> int:
        return getattr(obj, "review_count", 0)

    def get_enrolled_count(self, obj) -> int:
        return getattr(obj, "enrolled_count", 0)


class CourseDetailSerializer(CourseListSerializer):
    lessons = serializers.SerializerMethodField()
    reviews = CourseReviewSerializer(many=True, read_only=True)

    class Meta(CourseListSerializer.Meta):
        fields = CourseListSerializer.Meta.fields + (
            "description",
            "lessons",
            "reviews",
        )

    def get_lessons(self, obj) -> list[dict]:
        request = self.context.get("request")
        is_owner = (
            request
            and request.user.is_authenticated
            and (request.user.role == "ADMIN" or obj.instructor_id == request.user.pk)
        )
        qs = obj.lessons.order_by("order")
        if not is_owner:
            qs = qs.filter(is_published=True)
        return LessonSerializer(qs, many=True).data


class CourseWriteSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(
        max_length=255,
        required=False,
        allow_blank=False,
        default="",
    )
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, required=False
    )

    class Meta:
        model = Course
        fields = (
            "title",
            "slug",
            "description",
            "category",
            "tags",
            "thumbnail",
            "price",
            "level",
            "language",
            "is_published",
        )

    def validate(self, data):
        if not data.get("slug") and data.get("title"):
            data["slug"] = slugify(data.get("title", ""))
        return data

    def validate_slug(self, value):
        # empty string from default is handled in validate()
        return value or ""

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
