from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password

from rest_framework import serializers

from apps.users.models import CustomUser, UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )

    class Meta:
        model = CustomUser
        fields = ("email", "password", "full_name")

    def create(self, validated_data):
        return CustomUser.objects.create_user(
            email=validated_data["email"],
            full_name=validated_data["full_name"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").lower().strip()
        password = attrs.get("password")
        user = authenticate(
            request=self.context.get("request"), email=email, password=password
        )
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user,
        }


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField(read_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("phone", "country", "linkedin_url", "notification_preferences")


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = ("email", "full_name", "role", "avatar", "bio", "profile")
        read_only_fields = ("email", "role")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("profile", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data is not None:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(
        write_only=True, validators=[validate_password]
    )

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user
