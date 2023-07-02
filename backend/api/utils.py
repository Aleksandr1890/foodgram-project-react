from django.db.models import Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response

from recipes.models import Recipe, RecipeIngredient


def create(request, pk, model, serializer):
    """Добавить рецепт в избранное или список покупок."""
    recipe = get_object_or_404(Recipe, pk=pk)
    if model.objects.filter(user=request.user, recipe=recipe).exists():
        return Response(
            {'errors': 'Рецепт уже есть в избранном/списке покупок'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    model.objects.get_or_create(user=request.user, recipe=recipe)
    data = serializer(recipe).data
    return Response(data, status=status.HTTP_201_CREATED)


def delete(request, pk, model):
    """Удалить рецепт из избранного или списка покупок."""
    recipe = get_object_or_404(Recipe, pk=pk)
    if model.objects.filter(user=request.user, recipe=recipe).exists():
        follow = get_object_or_404(
            model, user=request.user,
            recipe=recipe
        )
        follow.delete()
        return Response(
            'Рецепт успешно удален из избранного/списка покупок',
            status=status.HTTP_204_NO_CONTENT
        )
    return Response(
        {'errors': 'Данного рецепта не было в избранном/списке покупок'},
        status=status.HTTP_400_BAD_REQUEST
    )


def recipe_ingredient_create(ingredients_data, models, recipe):
    """Функция для добавления/обновления рецепта."""
    bulk_create_data = (
        models(
            recipe=recipe,
            ingredient=ingredient_data['ingredient'],
            amount=ingredient_data['amount']
        )
        for ingredient_data in ingredients_data
    )
    models.objects.bulk_create(bulk_create_data)


def format_shopping_list(user, page, buffer):
    """Форматировать список покупок."""
    shopping_list = RecipeIngredient.objects.filter(
        recipe__cart__user=user).values(
        'ingredient__name',
        'ingredient__measurement_unit'
    ).annotate(
        amount=Sum('amount')
    ).order_by()
    x_position, y_position = 50, 800
    if shopping_list:
        page.setFont('Arial', 14)
        indent = 20
        page.drawString(x_position, y_position, 'Cписок покупок:')
        for index, recipe in enumerate(shopping_list, start=1):
            page.drawString(
                x_position, y_position - indent,
                f'{index}. {recipe["ingredient__name"]} - '
                f'{recipe["amount"]} '
                f'{recipe["ingredient__measurement_unit"]}.'
            )
            y_position -= 15
            if y_position <= 50:
                page.showPage()
                y_position = 800
        page.save()
        buffer.seek(0)
        return buffer
    page.setFont('Arial', 24)
    page.drawString(
        x_position,
        y_position,
        'Cписок покупок пуст!'
    )
    page.save()
    buffer.seek(0)
    return buffer
