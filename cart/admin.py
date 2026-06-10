from django.contrib import admin
from .models import CartItem, Address


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display  = ['shoe', 'user', 'session_key', 'size', 'quantity', 'added_at']
    list_filter   = ['added_at']
    search_fields = ['user__username', 'shoe__name', 'session_key']
    readonly_fields = ['added_at', 'updated_at']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'user', 'city', 'state', 'pincode', 'is_default']
    list_filter   = ['state', 'is_default']
    search_fields = ['user__username', 'full_name', 'city', 'pincode']
