from rest_framework import serializers

from apps.companies.models import Company, Employee
from apps.reports.models import ReportExportJob
from apps.users.models import Roles


def user_can_access_company(user, company):
    if user.role == Roles.ADMIN:
        return True
    if user.role == Roles.HR_MANAGER:
        return Employee.objects.filter(
            user=user,
            company=company,
            is_hr_manager=True,
        ).exists()
    return False


class ReportExportJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportExportJob
        fields = ("company", "report_type", "file_format", "parameters")

    def validate_company(self, company):
        request = self.context["request"]
        if not user_can_access_company(request.user, company):
            raise serializers.ValidationError(
                "You cannot export reports for this company."
            )
        return company


class ReportExportJobSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = ReportExportJob
        fields = (
            "id",
            "company",
            "report_type",
            "file_format",
            "parameters",
            "status",
            "gcs_object_path",
            "download_url",
            "signed_url_expires_at",
            "error_message",
            "started_at",
            "finished_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_download_url(self, obj) -> str | None:
        if obj.status != ReportExportJob.Status.READY or not obj.signed_url:
            return None
        request = self.context.get("request")
        if request and obj.signed_url.startswith("/"):
            return request.build_absolute_uri(obj.signed_url)
        return obj.signed_url


class ReportQuerySerializer(serializers.Serializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())

    def validate_company(self, company):
        request = self.context["request"]
        if not user_can_access_company(request.user, company):
            raise serializers.ValidationError(
                "You cannot access reports for this company."
            )
        return company
