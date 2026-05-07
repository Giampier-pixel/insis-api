from django.contrib.auth import get_user_model

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import Roles
from apps.users.permissions import IsAdmin
from apps.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MessageSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserSerializer,
)

User = get_user_model()


class RegisterView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["auth"],
        request=RegisterSerializer,
        responses={201: UserSerializer},
    )
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

    @extend_schema(
        tags=["auth"],
        request=LoginSerializer,
        responses={200: TokenPairSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return Response(
            {"access": data["access"], "refresh": data["refresh"]},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["auth"],
        request=LogoutSerializer,
        responses={205: None, 400: MessageSerializer},
    )
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
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=["auth"],
        request=UserSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        tags=["auth"],
        request=ChangePasswordSerializer,
        responses={200: MessageSerializer},
    )
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
        data = [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role,
                "is_active": u.is_active,
            }
            for u in users
        ]
        return Response(data)

    @extend_schema(tags=["admin"])
    def patch(self, request):
        user_id = request.data.get("id")
        if not user_id:
            return Response({"id": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        allowed = {"full_name", "role", "is_active"}
        for field in allowed & set(request.data.keys()):
            setattr(user, field, request.data[field])
        user.save()

        if "role" in request.data and request.data["role"] not in [r.value for r in Roles]:
            return Response({"role": ["Invalid role."]}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active,
        })
