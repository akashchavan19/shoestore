from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model  = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['phone', 'avatar', 'is_email_verified', 'is_first_time_user']


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']


# Re-register User with our custom admin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
