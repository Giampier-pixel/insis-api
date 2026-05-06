from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models

from apps.core.models import (
    SoftDeleteModel,
    SoftDeleteQuerySet,
    TimestampedModel,
)


class Roles(models.TextChoices):
    STUDENT = "STUDENT", "Student"
    INSTRUCTOR = "INSTRUCTOR", "Instructor"
    ADMIN = "ADMIN", "Admin"
    HR_MANAGER = "HR_MANAGER", "HR Manager"
    SUPPORT = "SUPPORT", "Support"


class CustomUserQuerySet(SoftDeleteQuerySet):
    pass


class CustomUserManager(BaseUserManager):
    def get_queryset(self):
        return CustomUserQuerySet(self.model, using=self._db).alive()

    def create_user(self, email, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email).lower().strip()
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Roles.ADMIN)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, full_name, password, **extra_fields)


class CustomUserAllObjectsManager(BaseUserManager):
    def get_queryset(self):
        return CustomUserQuerySet(self.model, using=self._db)


class CustomUser(TimestampedModel, SoftDeleteModel, AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = CustomUserManager()
    all_objects = CustomUserAllObjectsManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)


class UserProfile(TimestampedModel):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name="profile"
    )
    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True)
    notification_preferences = models.JSONField(default=dict)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self):
        return f"Profile of {self.user.email}"
