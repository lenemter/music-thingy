from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Поле Email обязательно для заполнения")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Суперпользователь должен иметь is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Суперпользователь должен иметь is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    # Убираем дефолтный username из модели
    username = None  # type: ignore

    email = models.EmailField("email address", unique=True)
    display_name = models.CharField("Display name", max_length=50, blank=True, default="")

    objects = UserManager()

    # Указываем, что email теперь является главным логином
    USERNAME_FIELD = "email"

    # Поля, которые createsuperuser дополнительно спросит в консоли
    REQUIRED_FIELDS = ["display_name"]

    def __str__(self) -> str:
        return self.display_name or self.email
