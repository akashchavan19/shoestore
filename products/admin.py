from django.contrib import admin
from django.utils.html import format_html
from .models import Shoe


@admin.register(Shoe)
class ShoeAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand', 'category', 'price', 'is_active', 'image_preview', 'created_at']
    list_filter = ['category', 'brand', 'is_active']
    search_fields = ['name', 'brand']
    prepopulated_fields = {'slug': ('brand', 'name')}
    list_editable = ['is_active', 'price']
    ordering = ['-created_at']
    readonly_fields = ['image_preview', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'slug', 'brand', 'category', 'price', 'is_active')
        }),
        ('Details', {
            'fields': ('description', 'available_sizes')
        }),
        ('Image', {
            'fields': ('image', 'image_preview')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="60" height="60" style="object-fit:cover;border-radius:4px;" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Preview'
