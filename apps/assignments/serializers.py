from rest_framework import serializers

from apps.assignments.models import AssignmentTarget, CompletionRecord, CourseAssignment
from apps.companies.models import Department


class CompletionRecordSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(
        source="employee.user.email", read_only=True
    )
    employee_full_name = serializers.CharField(
        source="employee.user.full_name", read_only=True
    )

    class Meta:
        model = CompletionRecord
        fields = (
            "id",
            "employee",
            "employee_email",
            "employee_full_name",
            "completed",
            "completed_at",
            "score",
        )
        read_only_fields = fields


class AssignmentTargetSerializer(serializers.ModelSerializer):
    employee_email = serializers.EmailField(
        source="employee.user.email", read_only=True
    )
    employee_full_name = serializers.CharField(
        source="employee.user.full_name", read_only=True
    )
    completion = CompletionRecordSerializer(source="completion_record", read_only=True)

    class Meta:
        model = AssignmentTarget
        fields = ("id", "employee", "employee_email", "employee_full_name", "completion")
        read_only_fields = fields


class AssignmentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    assigned_by_email = serializers.EmailField(
        source="assigned_by.email", read_only=True
    )
    assigned_by_name = serializers.CharField(
        source="assigned_by.full_name", read_only=True
    )
    total_targets = serializers.SerializerMethodField()
    completed_targets = serializers.SerializerMethodField()
    completion_pct = serializers.SerializerMethodField()

    class Meta:
        model = CourseAssignment
        fields = (
            "id",
            "course",
            "course_title",
            "company",
            "company_name",
            "assigned_by_email",
            "assigned_by_name",
            "scope",
            "due_date",
            "is_mandatory",
            "is_active",
            "total_targets",
            "completed_targets",
            "completion_pct",
            "created_at",
        )

    def get_total_targets(self, obj) -> int:
        return getattr(obj, "total_targets", obj.targets.count())

    def get_completed_targets(self, obj) -> int:
        return getattr(obj, "completed_targets", 0)

    def get_completion_pct(self, obj) -> float:
        total = self.get_total_targets(obj)
        done = self.get_completed_targets(obj)
        if total == 0:
            return 0
        return round(done / total * 100, 1)


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseAssignment
        fields = ("course", "company", "scope", "due_date", "is_mandatory")

    def validate(self, data):
        # HR validation happens in the view (user context needed)
        return data


class AssignDepartmentSerializer(serializers.Serializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
