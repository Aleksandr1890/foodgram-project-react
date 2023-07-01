from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    #CustomAuthToken,
    set_password,
    TagViewSet,
    IngredientViewSet,
    RecipeViewSet,
    CustomUserViewSet,
)

app_name = 'api'


router = DefaultRouter()
router.register('users', CustomUserViewSet, basename='users')
router.register('tags', TagViewSet, basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('recipes', RecipeViewSet, basename='recipes')

urlpatterns = [
    #path('auth/token/login/', CustomAuthToken.as_view(), name='login'),
    path('users/set_password/', set_password, name='set_password'),
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
