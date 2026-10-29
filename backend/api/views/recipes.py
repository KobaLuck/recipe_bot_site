from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.filters import IngredientFilter, RecipeInlineFilter
from api.pagination import DefaultPagination
from api.permissions import IsAuthorOrReadOnly
from api.serializers.recipes import (IngredientSerializer,
                                     RecipeCreateUpdateSerializer,
                                     RecipeListSerializer,
                                     RecipeMinifiedSerializer, TagSerializer)
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag


class ShortLinkView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, recipe_id):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        relative = recipe.get_short_link()
        absolute = request.build_absolute_uri(relative)
        return Response({"short-link": absolute}, status=status.HTTP_200_OK)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = DefaultPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeInlineFilter

    def get_permissions(self):
        if self.action in ["list", "retrieve", "get_link"]:
            return [AllowAny()]
        if self.action in ["favorite", "shopping_cart", "create"]:
            return [IsAuthenticated()]
        return [IsAuthorOrReadOnly()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return RecipeCreateUpdateSerializer
        return RecipeListSerializer

    @action(detail=True, methods=["get"], url_path="get-link")
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        absolute_url = request.build_absolute_uri(recipe.get_short_link())
        return Response({"short-link": absolute_url})

    @action(
        detail=True, methods=["post", "delete"],
        permission_classes=[IsAuthenticated]
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "POST":
            if Favorite.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            fav = Favorite(user=request.user, recipe=recipe)
            fav.save()
            serializer = RecipeMinifiedSerializer(
                recipe, context={"request": request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted_count, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted_count:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True, methods=["post", "delete"],
        url_path="shopping_cart",
        permission_classes=[IsAuthenticated]
    )
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "POST":
            if ShoppingCart.objects.filter(
                user=request.user, recipe=recipe
            ).exists():
                return Response(status=status.HTTP_400_BAD_REQUEST)
            cart_item = ShoppingCart(user=request.user, recipe=recipe)
            cart_item.save()
            data = RecipeMinifiedSerializer(
                recipe, context={"request": request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted_count, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted_count:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        url_path="download_shopping_cart"
    )
    def download_shopping_cart(self, request):
        lines = (
            f"{it['name']} ({it['measurement_unit']}) — {it['total']}"
            for it in request.user.get_shopping_list()
        )
        response = HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")
        response['Content-Disposition'] = 'attachment; filename="shopping-list.txt"'
        return response
