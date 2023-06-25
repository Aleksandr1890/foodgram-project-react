from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import Tag, Ingredient, RecipeIngredient, Recipe
from users.models import User, Follow
from .utils import recipe_ingredient_create


class TokenSerializer(serializers.Serializer):
    """
    Сериализатор для получения и удаления токена авторизации.
    """
    password = serializers.CharField(
        label='Password'
    )
    email = serializers.EmailField(
        label='Email'
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )

            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class CustomUserSerializer(UserSerializer):
    """Сериализатор для работы с пользователями."""
    is_subscribed = SerializerMethodField(read_only=True)

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
            'id',
            'username',
            'first_name',
            'last_name',
            'password',
        )
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user


class SubscribeSerializer(CustomUserSerializer):
    """Сериализатор для подписки на пользователя."""
    recipes_count = SerializerMethodField()
    recipes = SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )
        read_only_fields = ('email', 'username', 'first_name', 'last_name')

    def validate(self, data):
        author = self.instance
        user = self.context.get('request').user
        if Follow.objects.filter(author=author, user=user).exists():
            raise ValidationError(
                detail='Вы уже подписаны на этого пользователя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        if user == author:
            raise ValidationError(
                detail='Вы не можете подписаться на самого себя!',
                code=status.HTTP_400_BAD_REQUEST
            )
        return data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=obj)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeGetSerializer(recipes, many=True, read_only=True)
        return serializer.data


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля."""
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)

    def validate_current_password(self, current_password):
        user = self.context['request'].user
        if authenticate(username=user.email, password=current_password):
            return current_password
        raise serializers.ValidationError(
            'Неверный текущий пароль', code='invalid data'
        )

    def validate_new_password(self, value):
        validate_password(value)
        return value

    def save(self, **kwargs):
        new_password = self.validated_data['new_password']
        user = self.context['request'].user
        user.set_password(new_password)
        user.save()
        return user


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
        read_only_fields = ('id', 'author', 'tags')

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients')
        ingredients_list = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients_list) != len(set(ingredients_list)):
            raise serializers.ValidationError(
                'Проверьте, какой-то ингредиент был выбран более 1 раза'
            )
        return data

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        tags_data = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        recipe_ingredient_create(ingredients_data, RecipeIngredient, recipe)
        return recipe

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


class RecipePostDeleteSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления и удаления рецепта."""
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
