from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model          = OrderItem
    extra          = 0
    readonly_fields = ['shoe', 'size', 'quantity', 'price_at_purchase', 'subtotal']
    can_delete     = False

    def subtotal(self, obj):
        return f'₹{obj.subtotal}'
    subtotal.short_description = 'Subtotal'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display   = ['id', 'user', 'status', 'total_amount', 'placed_at', 'updated_at']
    list_filter    = ['status']
    search_fields  = ['user__username', 'user__email', 'razorpay_order_id']
    readonly_fields = ['placed_at', 'updated_at', 'razorpay_order_id', 'razorpay_payment_id']
    inlines        = [OrderItemInline]
    ordering       = ['-placed_at']

    fieldsets = (
        ('Order Info', {
            'fields': ('user', 'address', 'status', 'total_amount')
        }),
        ('Payment', {
            'fields': ('razorpay_order_id', 'razorpay_payment_id'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('placed_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
