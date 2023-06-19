from django.contrib import admin

from .models import User


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    list_display_links = ('username',)
    search_fields = ('username',)
    list_filter = ('username', 'email',)
    empty_value_display = '-empty-'


admin.site.register(User, UserAdmin)
