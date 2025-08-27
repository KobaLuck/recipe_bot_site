from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class User(AbstractUser):
    avatar = models.ImageField(
        upload_to="users/",
        blank=True,
        default="",
        verbose_name="Аватар",
    )
    email = models.EmailField("Почта", unique=True)
    telegram_id = models.BigIntegerField(
        "Telegram ID",
        blank=True,
        null=True,
        unique=True,
        help_text="ID пользователя в Telegram для интеграции с ботом"
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "username",
        "first_name",
        "last_name",
    ]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.username

    def get_shopping_list(self):
        from recipes.models import RecipeIngredient

        ingredient_qs = (
            RecipeIngredient.objects
            .filter(recipe__in_carts__user=self)
            .annotate(
                name=models.F("ingredient__name"),
                measurement_unit=models.F("ingredient__measurement_unit"),
                total=models.Sum("amount"),
            )
            .values("name", "measurement_unit", "total")
        )
        return list(ingredient_qs)


class Subscription(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscriptions"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="subscribers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "author"],
                                    name="unique_subscription")
        ]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def clean(self):
        super().clean()
        if self.user == self.author:
            raise ValidationError("Нельзя подписаться на себя.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} подписан на {self.author}"
