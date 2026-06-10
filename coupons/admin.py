from django.contrib import admin
from .models import Coupon, CouponUsage


class CouponUsageInline(admin.TabularInline):
    model         = CouponUsage
    extra         = 0
    readonly_fields = ['user', 'order', 'discount_applied', 'used_at']
    can_delete    = False


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ['code', 'discount_type', 'discount_value', 'minimum_order_amount',
                     'max_uses', 'usage_count', 'valid_until', 'is_active', 'first_user_only']
    list_filter   = ['discount_type', 'is_active', 'first_user_only']
    search_fields = ['code', 'description']
    list_editable = ['is_active']
    readonly_fields = ['usage_count', 'created_at']
    inlines       = [CouponUsageInline]

    fieldsets = (
        ('Coupon Details', {
            'fields': ('code', 'description', 'is_active', 'first_user_only')
        }),
        ('Discount', {
            'fields': ('discount_type', 'discount_value', 'minimum_order_amount')
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'max_uses_per_user', 'usage_count')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

    def usage_count(self, obj):
        return obj.get_usage_count()
    usage_count.short_description = 'Times Used'


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display  = ['coupon', 'user', 'order', 'discount_applied', 'used_at']
    list_filter   = ['coupon', 'used_at']
    search_fields = ['user__username', 'coupon__code']
    readonly_fields = ['coupon', 'user', 'order', 'discount_applied', 'used_at']
