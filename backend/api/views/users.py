from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.pagination import DefaultPagination
from api.serializers.users import (
    UserCreateSerializer,
    UserResponseSerializer,
    SubscriptionSerializer,
    SubscriptionCreateSerializer,
    PasswordChangeSerializer,
    SetAvatarSerializer,
)
from users.models import Subscription

User = get_user_model()


class UserViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = User.objects.all()
    pagination_class = DefaultPagination

    def get_permissions(self):
        if self.action in ("create", "list", "retrieve"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "subscriptions":
            return SubscriptionSerializer
        if self.action in ("subscribe", "unsubscribe"):
            return SubscriptionCreateSerializer
        return UserResponseSerializer

    @action(
        detail=False, methods=["get"], url_path="subscriptions",
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        qs = Subscription.objects.filter(
            user=request.user).select_related('author')
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True,
                                         context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True, methods=["post", "delete"], url_path="subscribe",
        permission_classes=[IsAuthenticated]
    )
    @transaction.atomic
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        if request.method == "POST":
            if author == request.user:
                return Response({"detail": "Нельзя подписаться на себя."},
                                status=status.HTTP_400_BAD_REQUEST)
            sub, created = Subscription.objects.get_or_create(
                user=request.user, author=author)
            if not created:
                return Response({"detail": "Вы уже подписаны."},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(sub,
                                                context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author).delete()
        if not deleted:
            return Response({"detail": "Вы не были подписаны."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_object(self):
        if self.action == "me":
            return self.request.user
        return super().get_object()

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        serializer = UserResponseSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        user = request.user

        if request.method == "PUT":
            serializer = SetAvatarSerializer(
                instance=user, data=request.data, context={"request": request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(
                {"avatar": request.build_absolute_uri(user.avatar.url)},
                status=status.HTTP_200_OK,
            )

        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["post"],
        url_path="set_password",
        permission_classes=[IsAuthenticated],
    )
    def set_password(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        current = serializer.validated_data["current_password"]
        new = serializer.validated_data["new_password"]
        user = request.user
        if not user.check_password(current):
            return Response(
                {"current_password": "Неправильный пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new)
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
