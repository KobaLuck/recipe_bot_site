import base64
import binascii
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from users.models import Subscription

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:"):
            try:
                header, base64_str = data.split(";base64,", 1)
                decoded_file = base64.b64decode(base64_str, validate=True)
            except (ValueError, binascii.Error):
                raise serializers.ValidationError("Некорректное изображение Base64.")
            ext = header.split("/")[-1]
            file_name = f"{uuid4().hex}.{ext}"
            data = ContentFile(decoded_file, name=file_name)
        return super().to_internal_value(data)


class UserCreateSerializer(DjoserUserSerializer):
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "id", "email", "username", "first_name", "last_name", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserResponseSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "email",
            "id",
            "username",
            "first_name",
            "last_name",
            "avatar",
            "is_subscribed",
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        return bool(
            request
            and not request.user.is_anonymous
            and obj.subscribers.filter(user=request.user).exists()
        )


class SetAvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ("avatar",)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()


class SubscriptionCreateSerializer(serializers.Serializer):
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='author'
    )

    def validate_author_id(self, author):
        user = self.context['request'].user
        if author == user:
            raise serializers.ValidationError("Нельзя подписаться на себя.")
        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError("Вы уже подписаны.")
        return author

    def create(self, validated_data):
        return Subscription.objects.create(
            user=self.context['request'].user,
            author=validated_data['author']
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    avatar = serializers.SerializerMethodField()
    is_subscribed = serializers.BooleanField(default=True)
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='author.recipes.count',
                                             read_only=True)

    class Meta:
        model = Subscription
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'avatar', 'is_subscribed',
            'recipes', 'recipes_count'
        )

    def get_avatar(self, obj):
        request = self.context.get('request')
        avatar = obj.author.avatar
        if avatar and hasattr(avatar, 'url'):
            return request.build_absolute_uri(avatar.url)
        return None

    def get_recipes(self, obj):
        from api.serializers.recipes import RecipeMinifiedSerializer

        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes_qs = obj.author.recipes.order_by('-created')
        if limit is not None:
            try:
                limit = int(limit)
            except (TypeError, ValueError):
                raise serializers.ValidationError(
                    {'recipes_limit': 'Должен быть целым числом.'})
            if limit < 0:
                raise serializers.ValidationError(
                    {'recipes_limit': 'Должен быть неотрицательным числом.'})
            recipes_qs = recipes_qs[:limit]
        return RecipeMinifiedSerializer(
            recipes_qs, many=True, context=self.context).data
