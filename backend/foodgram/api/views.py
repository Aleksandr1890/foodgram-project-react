from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets, permissions, exceptions
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly, \
    IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from .models import Follow
from api.serializers import TokenSerializer, UserSerializer, UserCreateSerializer, \
    SetPasswordSerializer, UserFollowSerializer, CustomUserSerializer, \
    CustomUserCreateSerializer


class CustomAuthToken(ObtainAuthToken):
    """Авторизация пользователей."""

    def post(self, request, *args, **kwargs):
        serializer = TokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {'auth_token': token.key},
            status=status.HTTP_201_CREATED
        )


class UserViewSet(viewsets.ModelViewSet):
    """
    Создает или возвращает данные пользователей.
    """
    queryset = User.objects.all()

    @action(
        methods=['get'],
        detail=False,
        permission_classes=[IsAuthenticated],
        serializer_class=CustomUserSerializer,
    )
    def me(self, request):
        user = User.objects.get(username=request.user.username)
        serializer = self.get_serializer(user,)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CustomUserCreateSerializer
        return CustomUserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            permission_classes = (AllowAny,)
        else:
            permission_classes = (IsAuthenticated,)
        return [permission() for permission in permission_classes]

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated],
        serializer_class=UserFollowSerializer,
    )
    def subscribe(self, request, pk=None):
        user = User.objects.get(username=request.user.username)
        author = get_object_or_404(User, id=pk)

        if request.method == 'POST':
            if user.id == author.id:
                content = {'errors': 'Нельзя подписаться на самого себя'}
                return Response(content, status=status.HTTP_400_BAD_REQUEST)
            if Follow.objects.filter(
                user=user,
                author=author
            ).exists():
                raise exceptions.ValidationError('Подписка уже оформлена.')
            else:
                serializer = UserFollowSerializer(
                    author,
                    data=request.data,
                    context={"request": request}
                )
                if serializer.is_valid(raise_exception=True):
                    Follow.objects.create(user=user, author=author)
                    print(serializer.data)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif self.request.method == 'DELETE':
            if not Follow.objects.filter(
                user=user,
                author=author
            ).exists():
                raise exceptions.ValidationError(
                    'Подписка не была оформлена, либо уже удалена.'
                )

            subscription = get_object_or_404(
                Follow,
                user=user,
                author=author
            )
            subscription.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        permission_classes=[IsAuthenticated]
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = UserFollowSerializer(
            pages,
            many=True,
            context={'request': request})
        return self.get_paginated_response(serializer.data)


@api_view(['post'])
@permission_classes([IsAuthenticated])
def set_password(request):
    """Изменяет пароль пользователя."""
    serializer = SetPasswordSerializer(
        data=request.data,
        context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
