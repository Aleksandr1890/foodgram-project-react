from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.fields import SerializerMethodField
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password
from djoser.serializers import UserCreateSerializer, UserSerializer

from .models import Follow
from users.models import User


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
    """
    Сериализатор для работы со списком пользователей.
    """
    username = serializers.RegexField(
        validators=[UniqueValidator(queryset=User.objects.all())],
        max_length=150,
        regex=r'^[a-zA-Z0-9@.+-_]+$'
    )
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all())],
        max_length=254,
    )
    first_name = serializers.CharField(
        max_length=150,
        required=True
    )
    last_name = serializers.CharField(
        max_length=150,
        required=True
    )

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name'
        )


class UserFollowSerializer(CustomUserSerializer):
    """
    Пользовательский сериализатор.
    """
    #id = serializers.CharField(source='author.id', read_only=True)
    #email = serializers.ReadOnlyField(source='author.email')
    #username = serializers.ReadOnlyField(source='author.username')
    #first_name = serializers.ReadOnlyField(source='author.first_name')
    #last_name = serializers.ReadOnlyField(source='author.last_name')
    is_subscribed = SerializerMethodField()

    class Meta:
        model = Follow
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
                  'is_subscribed'
            #, 'recipes', 'recipes_count'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Follow.objects.filter(user=user, author=obj).exists()
        return False


    #def validate(self, data):
    #    author = self.instance
    #    user = self.context.get('request').user
    #    if Follow.objects.filter(author=author, user=user).exists():
    #        raise ValidationError(
    #            detail='Вы уже подписаны на этого пользователя!',
    #            code=status.HTTP_400_BAD_REQUEST
    #        )
    #    if user == author:
    #        raise ValidationError(
    #            detail='Вы не можете подписаться на самого себя!',
    #            code=status.HTTP_400_BAD_REQUEST
    #        )
    #    return data


class CustomUserCreateSerializer(UserCreateSerializer):
    """
    Сериализатор для создания пользователя.
    """
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'password',)
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


class UserEditSerializer(serializers.ModelSerializer):
    username = serializers.RegexField(
        validators=[UniqueValidator(queryset=User.objects.all())],
        max_length=150,
        regex=r'^[a-zA-Z0-9@.+-_]+$'
    )

    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name',
            'last_name'
        )


class SetPasswordSerializer(serializers.Serializer):
    """
    Сериализатор для изменения пароля.
    """
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

