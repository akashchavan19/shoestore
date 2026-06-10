"""
coupons/models.py

Design decisions:
- Coupon code stored uppercase — normalised at save time
- discount_type: PERCENTAGE or FLAT
- max_uses: None = unlimited
- max_uses_per_user: default 1 — prevents abuse
- is_active: soft disable without deleting
- CouponUsage tracks every application — audit trail + usage counting
- DB constraints prevent negative values at DB level
"""

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class Coupon(models.Model):

    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage (%)'
        FLAT       = 'flat',       'Flat Amount (₹)'

    code          = models.CharField(
        max_length=30,
        unique=True,
        help_text='Coupon code — stored uppercase. e.g. WELCOME10',
    )
    description   = models.CharField(
        max_length=200,
        blank=True,
        help_text='Shown to user when coupon is applied.',
    )
    discount_type  = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text='Percentage (0-100) or flat INR amount.',
    )
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Minimum cart total required to use this coupon.',
    )
    # None = unlimited total uses
    max_uses      = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Max total uses across all users. Leave blank for unlimited.',
    )
    max_uses_per_user = models.PositiveIntegerField(
        default=1,
        help_text='Max times one user can use this coupon.',
    )
    # None = never expires
    valid_from    = models.DateTimeField(default=timezone.now)
    valid_until   = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Leave blank for no expiry.',
    )
    is_active     = models.BooleanField(default=True)
    # First-user only flag — used by FIRSTUSER coupon
    first_user_only = models.BooleanField(
        default=False,
        help_text='If True, only users who have never placed an order can use this.',
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['code'])]

    def __str__(self):
        return f'{self.code} — {self.get_discount_type_display()} {self.discount_value}'

    def save(self, *args, **kwargs):
        # Always store code uppercase
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def get_usage_count(self) -> int:
        return self.usages.count()

    def calculate_discount(self, order_total: Decimal) -> Decimal:
        """
        Calculates the discount amount for a given order total.
        Caps percentage discount at the order total (can't discount more than total).
        Returns Decimal rounded to 2dp.
        """
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = (order_total * self.discount_value / Decimal('100')).quantize(Decimal('0.01'))
        else:
            discount = self.discount_value

        # Discount cannot exceed order total
        return min(discount, order_total)


class CouponUsage(models.Model):
    """
    Audit trail of every coupon application.
    One row per (user + coupon + order).
    """
    coupon     = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coupon_usages')
    order      = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='coupon_usages',
        null=True,
        blank=True,
    )
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    used_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['coupon', 'user']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f'{self.user.username} used {self.coupon.code} — ₹{self.discount_applied} off'
