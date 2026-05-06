from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    MessageSerializer,
    RegisterSerializer,
    TokenPairSerializer,
    UserSerializer,
)


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
