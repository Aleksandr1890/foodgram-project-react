from django.urls import path, include, re_path
from rest_framework.authtoken import views
from rest_framework.routers import DefaultRouter

from .views import CustomAuthToken, UserViewSet, set_password

app_name = 'api'


#class NoPutRouter(DefaultRouter):
#    """
#    Роутер отключает метод "Put".
#    """
#    def get_method_map(self, viewset, method_map):
#        bound_methods = super().get_method_map(viewset, method_map)
#        if 'put' in bound_methods.keys():
#            del bound_methods['put']
#        return bound_methods


router = DefaultRouter()
router.register('users', UserViewSet)

urlpatterns = [
    path('auth/token/login/', CustomAuthToken.as_view(), name='login'),
    path('users/set_password/', set_password, name='set_password'),
    path('', include(router.urls)),
    path('auth/', include('djoser.urls')),
    re_path(r'^auth/', include('djoser.urls.authtoken')),
]
