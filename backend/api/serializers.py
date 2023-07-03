from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import Tag, Ingredient, RecipeIngredient, Recipe
from users.models import Follow
from .utils import recipe_ingredient_create

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор для работы с пользователями."""
    is_subscribed = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Follow.objects.filter(user=user, author=obj).exists()


class CustomUserCreateSerializer(UserCreateSerializer):
    """
    Сериализатор для создания пользователя.
    """
    class Meta:
        model = User
        fields = (
            'email',
            'username',
            'first_name',
            'last_name',
            'password',
        )

    def validate_password(self, value):
        validate_password(value)
        return value


class FollowSerializer(serializers.ModelSerializer):
    """Сериализатор для подписки на пользователя."""
    id = serializers.ReadOnlyField(source='author.id')
    email = serializers.ReadOnlyField(source='author.email')
    username = serializers.ReadOnlyField(source='author.username')
    first_name = serializers.ReadOnlyField(source='author.first_name')
    last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        return Follow.objects.filter(
            user=obj.user, author=obj.author
        ).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        queryset = Recipe.objects.filter(author=obj.author)
        if limit:
            queryset = queryset[:int(limit)]
        return RecipeFollowSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj.author).count()


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeGetSerializer(serializers.ModelSerializer):
    """Получить ингредиенты для рецепта."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')
        validators = [
            UniqueTogetherValidator(
                queryset=RecipeIngredient.objects.all(),
                fields=['ingredient', 'recipe']
            )
        ]


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор ингредиентов для рецепта"""
    recipe = serializers.PrimaryKeyRelatedField(read_only=True)
    amount = serializers.IntegerField(write_only=True, min_value=1)
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount', 'recipe')


class RecipeFollowSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с функциями shopping_cart и favorite.
    """
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeGetSerializer(serializers.ModelSerializer):
    """Сериализатор для получения рецептов"""
    image = Base64ImageField(max_length=None)
    ingredients = serializers.SerializerMethodField()
    author = CustomUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )
        read_only_fields = ('id', 'author',)

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.favorites.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return obj.cart.filter(user=user).exists()

    def get_ingredients(self, obj):
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=obj)
        return IngredientRecipeGetSerializer(
            recipe_ingredients,
            many=True
        ).data


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с рецептами"""
    ingredients = IngredientRecipeSerializer(many=True)
    author = UserSerializer(read_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    image = Base64ImageField(max_length=None, use_url=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'name',
            'text',
            'ingredients',
            'tags',
            'cooking_time',
            'image'
        )

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        ingredients_list = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_list) != len(set(ingredients_list)):
            raise serializers.ValidationError(
                'Проверьте, какой-то ингредиент был выбран более 1 раза'
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        recipe_ingredient_create(ingredients_data, RecipeIngredient, recipe)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        if 'tags' in self.validated_data:
            tags_data = validated_data.pop('tags')
            instance.tags.set(tags_data)
        if 'ingredients' in self.validated_data:
            ingredients_data = validated_data.pop('ingredients')
            amount_set = RecipeIngredient.objects.filter(
                recipe__id=instance.id
            )
            amount_set.delete()
            recipe_ingredient_create(
                ingredients_data, RecipeIngredient, instance
            )
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        self.fields.pop('ingredients')
        self.fields.pop('tags')
        representation = super().to_representation(instance)
        representation['ingredients'] = IngredientRecipeGetSerializer(
            RecipeIngredient.objects.filter(recipe=instance), many=True
        ).data
        representation['tags'] = TagSerializer(
            instance.tags, many=True
        ).data
        return representation
