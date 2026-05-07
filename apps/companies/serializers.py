from rest_framework import serializers

from apps.companies.models import Company, Department, Employee


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ("id", "name", "employee_count", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")

    def get_employee_count(self, obj) -> int:
        return obj.employees.count()


class CompanySerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()
    department_count = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = (
            "id",
            "name",
            "ruc",
            "logo",
            "industry",
            "website",
            "employee_count",
            "department_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_employee_count(self, obj) -> int:
        return obj.employees.count()

    def get_department_count(self, obj) -> int:
        return obj.departments.count()

    def validate_ruc(self, value):
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError("RUC must be exactly 11 digits.")
        return value


class EmployeeSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    department_name = serializers.CharField(
        source="department.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "email",
            "full_name",
            "company",
            "company_name",
            "department",
            "department_name",
            "is_hr_manager",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "user",
            "company",
            "email",
            "full_name",
            "company_name",
            "department_name",
            "created_at",
            "updated_at",
        )

    def validate(self, data):
        department = data.get("department")
        if (
            department
            and self.instance
            and department.company_id != self.instance.company_id
        ):
            raise serializers.ValidationError(
                {"department": "Department does not belong to this employee's company."}
            )
        return data


class EmployeeCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=255)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    is_hr_manager = serializers.BooleanField(default=False)

    def validate_email(self, value):
        return value.lower().strip()


class EmployeeBulkImportSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Only CSV files are accepted.")
        return value


class CompanyStatsSerializer(serializers.Serializer):
    total_employees = serializers.IntegerField()
    total_departments = serializers.IntegerField()
    hr_managers = serializers.IntegerField()
