import io

from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import (
    TokenSerializer, SetPasswordSerializer, CustomUserSerializer,
    TagSerializer, IngredientSerializer,
    RecipeGetSerializer, RecipeSerializer, RecipeFollowSerializer,
    RecipePostDeleteSerializer, SubscribeSerializer
)
from recipes.models import (
    Tag,
    Ingredient,
    Recipe,
    Favourite,
    ShoppingCart
)
from users.models import Follow
from .filters import IngredientFilter, RecipeFilter
from .mixins import ListRetrieveViewSet
from .pagination import CustomPageSizePagination
from .permissions import IsAuthorOrReadOnly
from .utils import create, delete, format_shopping_list

User = get_user_model()


#class CustomAuthToken(ObtainAuthToken):
#    """Авторизация пользователей."""
#    def post(self, request, *args, **kwargs):
#        serializer = TokenSerializer(data=request.data)
#        serializer.is_valid(raise_exception=True)
#        user = serializer.validated_data['user']
#        token, created = Token.objects.get_or_create(user=user)
#        return Response(
#            {'auth_token': token.key},
#            status=status.HTTP_201_CREATED
#        )


class CustomUserViewSet(UserViewSet):
    """Вьюсет для работы с пользователем."""
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPageSizePagination

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)

        if request.method == 'POST':
            serializer = SubscribeSerializer(
                author,
                data=request.data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Follow.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        subscription = get_object_or_404(
            Follow,
            user=user,
            author=author
        )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


@api_view(['post'])
@permission_classes([IsAuthenticated])
def set_password(request):
    """Изменяет пароль пользователя."""
    serializer = SetPasswordSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(ListRetrieveViewSet):
    """Вьюсет для работы с тегами."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class IngredientViewSet(ListRetrieveViewSet):
    """Вьюсет для работы с ингредиентами с поиском по названию"""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами"""
    filterset_class = RecipeFilter
    pagination_class = CustomPageSizePagination
    queryset = Recipe.objects.all()

    def get_queryset(self):
        is_favorited = self.request.query_params.get('is_favorited')
        is_in_shopping_cart = self.request.query_params.get(
            'is_in_shopping_cart'
        )
        if is_favorited or is_in_shopping_cart:
            if int(is_favorited) == 1:
                return Recipe.objects.filter(favorites__user=self.request.user)
            if int(is_in_shopping_cart) == 1:
                return Recipe.objects.filter(cart__user=self.request.user)
            return Recipe.objects.none()
        return Recipe.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            'Рецепт успешно удален',
            status=status.HTTP_204_NO_CONTENT
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return RecipeGetSerializer
        return RecipeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (IsAuthorOrReadOnly,)
        return [permission() for permission in permission_classes]

    def post(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {'errors': 'Рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = RecipePostDeleteSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, model, user, pk):
        obj = model.objects.filter(user=user, recipe__id=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Рецепт уже удален!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['POST', 'DELETE'],)
    def favorite(self, request, pk):
        if self.request.method == 'POST':
            return create(request, pk, Favourite, RecipeFollowSerializer)
        return delete(request, pk, Favourite)

    @action(detail=True, methods=['POST', 'DELETE'],)
    def shopping_cart(self, request, pk):
        if request.method == 'POST':
            return create(request, pk, ShoppingCart, RecipeFollowSerializer)
        return delete(request, pk, ShoppingCart)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Скачать список с ингредиентами."""

        buffer = io.BytesIO()
        page = canvas.Canvas(buffer)
        pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
        user = request.user
        buffer = format_shopping_list(user=user, page=page, buffer=buffer)
        return FileResponse(
            buffer,
            as_attachment=True,
            filename='shoppingcart.pdf'
        )
