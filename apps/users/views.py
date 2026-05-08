from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsAdmin
from apps.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MessageSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserAdminSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(tags=["auth"], request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"email": user.email, "full_name": user.full_name},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(tags=["auth"], request=LoginSerializer, responses={200: TokenPairSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            {
                "access": data["access"],
                "refresh": data["refresh"],
                "role": data["user"].role,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["auth"], request=LogoutSerializer, responses={205: None, 400: MessageSerializer})
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"detail": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["auth"], responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(tags=["auth"], request=UserSerializer, responses={200: UserSerializer})
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(tags=["auth"], request=ChangePasswordSerializer, responses={200: MessageSerializer})
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password updated successfully."}, status=status.HTTP_200_OK
        )


class UserListView(APIView):
    permission_classes = (IsAdmin,)

    @extend_schema(tags=["admin"])
    def get(self, request):
        users = User.objects.all().order_by("full_name")
        return Response(UserAdminSerializer(users, many=True).data)

    @extend_schema(tags=["admin"], request=UserAdminSerializer)
    def post(self, request):
        serializer = UserAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserAdminSerializer(user).data, status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    permission_classes = (IsAdmin,)

    def _get_user(self, pk):
        return get_object_or_404(User, pk=pk)

    @extend_schema(tags=["admin"])
    def patch(self, request, pk):
        user = self._get_user(pk)
        serializer = UserAdminSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserAdminSerializer(user).data)

    @extend_schema(tags=["admin"])
    def delete(self, request, pk):
        user = self._get_user(pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminReportView(APIView):
    permission_classes = (IsAdmin,)

    @extend_schema(tags=["admin"])
    def get(self, request):
        from apps.enrollments.models import Certificate, Enrollment

        total_students = User.objects.filter(role="STUDENT").count()
        total_courses = __import__("apps.courses.models", fromlist=["Course"]).Course.objects.count()
        total_certificates = Certificate.objects.filter(is_ready=True).count()

        recent = (
            Enrollment.objects.filter(completed=True)
            .select_related("student", "course")
            .order_by("-completed_at")[:10]
        )
        recent_data = [
            {
                "student_email": e.student.email,
                "student_name": e.student.full_name,
                "course_title": e.course.title,
                "completed_at": e.completed_at,
            }
            for e in recent
        ]

        return Response(
            {
                "total_students": total_students,
                "total_courses": total_courses,
                "total_certificates": total_certificates,
                "recent_completions": recent_data,
            }
        )
