from types import SimpleNamespace
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from api.serializers.users import Base64ImageField, SubscriptionCreateSerializer
from api.serializers.recipes import RecipeCreateUpdateSerializer
from recipes.models import Ingredient, Recipe, RecipeIngredient, ShoppingCart, Tag
from rest_framework.exceptions import ValidationError

class RecipeRegressionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='author', email='author@example.com', password='safe-test-pass')
        self.ingredient = Ingredient.objects.create(name='Flour', measurement_unit='g')
        self.tag = Tag.objects.create(name='Lunch', slug='lunch')
        self.recipe = Recipe.objects.create(author=self.user, name='Bread', text='Mix', cooking_time=10)
        self.recipe.tags.add(self.tag)
        RecipeIngredient.objects.create(recipe=self.recipe, ingredient=self.ingredient, amount=2)
        self.context = {'request': SimpleNamespace(user=self.user)}

    def test_invalid_base64_returns_validation_error(self):
        for value in ('data:image/png;broken', 'data:image/png;base64,%%%'):
            with self.assertRaises(ValidationError):
                Base64ImageField().run_validation(value)

    def test_partial_update_preserves_ingredients_and_tags(self):
        serializer = RecipeCreateUpdateSerializer(self.recipe,
            data={'name':'New name'}, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.assertEqual(self.recipe.recipe_ingredients.get().amount, 2)
        self.assertEqual(self.recipe.tags.count(), 1)

    def test_failed_update_rolls_back_ingredients(self):
        serializer = RecipeCreateUpdateSerializer(self.recipe, data={
            'ingredients':[{'id':self.ingredient.pk,'amount':7}],
            'tags':[self.tag.pk]}, partial=True, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch('api.serializers.recipes.RecipeIngredient.objects.bulk_create', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):serializer.save()
        self.assertEqual(self.recipe.recipe_ingredients.get().amount, 2)

    def test_shopping_list_combines_same_ingredient(self):
        other = Recipe.objects.create(author=self.user, name='Cake', text='Bake', cooking_time=20)
        RecipeIngredient.objects.create(recipe=other, ingredient=self.ingredient, amount=3)
        for recipe in (self.recipe, other):
            ShoppingCart.objects.create(user=self.user, recipe=recipe)
        self.assertEqual(self.user.get_shopping_list(), [
            {'name':'Flour','measurement_unit':'g','total':5}])

    def test_shopping_download_is_plain_text(self):
        ShoppingCart.objects.create(user=self.user, recipe=self.recipe)
        client = APIClient();client.force_authenticate(self.user)
        response = client.get('/api/recipes/download_shopping_cart/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Flour (g) — 2')

    def test_cannot_subscribe_to_self(self):
        serializer = SubscriptionCreateSerializer(data={'author_id':self.user.pk}, context=self.context)
        self.assertFalse(serializer.is_valid())

    def test_negative_recipe_limit_returns_400(self):
        reader = get_user_model().objects.create_user(username='reader', email='reader@example.com')
        client = APIClient();client.force_authenticate(reader)
        response = client.post(f'/api/users/{self.user.pk}/subscribe/?recipes_limit=-1')
        self.assertEqual(response.status_code, 400)
