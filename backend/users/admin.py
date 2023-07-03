from django.contrib import admin

from .models import User, Follow


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    list_display_links = ('username',)
    search_fields = ('username',)
    list_filter = ('username', 'email',)
    empty_value_display = '-empty-'


class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = ('user', 'author')
    list_filter = ('user', 'author')
    empty_value_display = '-empty-'


admin.site.register(User, UserAdmin)
admin.site.register(Follow, FollowAdmin)
