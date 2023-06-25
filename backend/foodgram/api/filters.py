import django_filters as filters

from recipes.models import Ingredient, Recipe, Tag
from users.models import User


class IngredientFilter(filters.FilterSet):
    """Фильтр по названию ингредиента."""
    name = filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    """Фильтр по тегам и автору."""
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())

    class Meta:
        model = Recipe
        fields = ('tags', 'author')
