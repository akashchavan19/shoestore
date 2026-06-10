"""
orders/models.py

Order lifecycle: pending → paid → processing → shipped → delivered → cancelled

Changes from Phase 3:
- Added coupon, discount_amount, final_amount fields
- final_amount = total_amount - discount_amount
- coupon stored as nullable FK — order may have no coupon
"""

from django.db import models
from django.contrib.auth.models import User
from cart.models import Address
from products.models import Shoe


class Order(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PAID       = 'paid',       'Paid'
        PROCESSING = 'processing', 'Processing'
        SHIPPED    = 'shipped',    'Shipped'
        DELIVERED  = 'delivered',  'Delivered'
        CANCELLED  = 'cancelled',  'Cancelled'

    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address          = models.ForeignKey(Address, on_delete=models.PROTECT)
    status           = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    total_amount     = models.DecimalField(max_digits=10, decimal_places=2,
                                           help_text='Cart total before discount.')

    # Coupon fields — nullable, only set when a coupon is applied
    coupon           = models.ForeignKey(
        'coupons.Coupon',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='orders',
    )
    discount_amount  = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text='Amount discounted by coupon.',
    )
    final_amount     = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        help_text='Amount actually charged = total_amount - discount_amount.',
    )

    # Razorpay fields
    razorpay_order_id   = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)

    placed_at  = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-placed_at']
        indexes  = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['razorpay_order_id']),
        ]

    def __str__(self):
        return f'Order #{self.id} — {self.user.username} ({self.status})'


class OrderItem(models.Model):
    order             = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    shoe              = models.ForeignKey(Shoe, on_delete=models.PROTECT)
    size              = models.CharField(max_length=10, blank=True)
    quantity          = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.quantity}x {self.shoe.name} (size {self.size})'

    @property
    def subtotal(self):
        return self.price_at_purchase * self.quantity
