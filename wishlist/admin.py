from django.contrib import admin
from .models import WishlistItem


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display  = ['user', 'shoe', 'added_at']
    list_filter   = ['added_at']
    search_fields = ['user__username', 'shoe__name']
    readonly_fields = ['added_at']
