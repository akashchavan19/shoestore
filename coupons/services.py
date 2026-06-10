"""
coupons/services.py

All coupon validation and application logic lives here.

Validation order (fail fast — check cheapest operations first):
1. Code exists and is active
2. Not expired
3. Not exceeded max total uses
4. User hasn't exceeded their personal usage limit
5. First-user-only check
6. Minimum order amount check

All checks happen BEFORE any DB writes.
Application happens atomically with order creation in OrderService.
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import Coupon, CouponUsage

logger = logging.getLogger('onistuka')


class CouponError(Exception):
    """Raised for all known coupon validation failures."""
    pass


class CouponService:

    @staticmethod
    def validate(code: str, user, order_total: Decimal) -> Coupon:
        """
        Validates a coupon code for a given user and order total.
        Runs all checks in order — raises CouponError on first failure.

        Args:
            code:        Coupon code string (case-insensitive)
            user:        Authenticated User instance
            order_total: Cart total as Decimal

        Returns:
            Valid Coupon instance

        Raises:
            CouponError: with a user-friendly message on any validation failure
        """
        code = code.upper().strip()

        # 1. Exists and active
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
        except Coupon.DoesNotExist:
            raise CouponError('Invalid coupon code.')

        # 2. Not expired
        now = timezone.now()
        if coupon.valid_from > now:
            raise CouponError('This coupon is not yet active.')
        if coupon.valid_until and coupon.valid_until < now:
            raise CouponError('This coupon has expired.')

        # 3. Max total uses
        if coupon.max_uses is not None:
            if coupon.get_usage_count() >= coupon.max_uses:
                raise CouponError('This coupon has reached its usage limit.')

        # 4. Per-user limit
        user_usage_count = CouponUsage.objects.filter(
            coupon=coupon, user=user
        ).count()
        if user_usage_count >= coupon.max_uses_per_user:
            raise CouponError('You have already used this coupon.')

        # 5. First-user-only check
        if coupon.first_user_only:
            try:
                if not user.profile.is_first_time_user:
                    raise CouponError('This coupon is only for first-time customers.')
            except Exception:
                raise CouponError('This coupon is only for first-time customers.')

        # 6. Minimum order amount
        if order_total < coupon.minimum_order_amount:
            raise CouponError(
                f'Minimum order amount of ₹{coupon.minimum_order_amount} required for this coupon.'
            )

        return coupon

    @staticmethod
    def get_discount_amount(coupon: Coupon, order_total: Decimal) -> Decimal:
        """Calculates discount without applying it. Used for preview in cart."""
        return coupon.calculate_discount(order_total)

    @staticmethod
    @transaction.atomic
    def apply_to_order(coupon: Coupon, user, order, discount_amount: Decimal):
        """
        Records coupon usage after order is created.
        Called inside OrderService.create_order_from_cart — same transaction.

        Args:
            coupon:          Validated Coupon instance
            user:            User who used the coupon
            order:           The Order the coupon was applied to
            discount_amount: Actual discount applied (pre-calculated)
        """
        CouponUsage.objects.create(
            coupon           = coupon,
            user             = user,
            order            = order,
            discount_applied = discount_amount,
        )
        logger.info(
            'Coupon applied: code=%s user=%s order=%s discount=₹%s',
            coupon.code, user.username, order.id, discount_amount
        )

    @staticmethod
    def get_first_user_coupon():
        """
        Returns the active first-user coupon if one exists.
        Used to auto-suggest coupon on cart page for new users.
        """
        return Coupon.objects.filter(
            is_active=True,
            first_user_only=True,
        ).first()
