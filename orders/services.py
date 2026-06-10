"""
orders/services.py

Updated for Phase 4 — handles optional coupon application.
All coupon validation happens BEFORE order creation.
Coupon usage recorded inside the same atomic transaction as order creation.
"""

import logging
from decimal import Decimal
from django.db import transaction

from .models import Order, OrderItem
from cart.services import CartService
from cart.models import Address

logger = logging.getLogger('onistuka')


VALID_TRANSITIONS = {
    Order.Status.PENDING:    [Order.Status.PAID,      Order.Status.CANCELLED],
    Order.Status.PAID:       [Order.Status.PROCESSING, Order.Status.CANCELLED],
    Order.Status.PROCESSING: [Order.Status.SHIPPED],
    Order.Status.SHIPPED:    [Order.Status.DELIVERED],
    Order.Status.DELIVERED:  [],
    Order.Status.CANCELLED:  [],
}


class OrderError(Exception):
    pass


class OrderService:

    @staticmethod
    @transaction.atomic
    def create_order_from_cart(user, address_id: int, coupon_code: str = '') -> Order:
        """
        Creates an Order from the user's current cart.
        Optionally applies a coupon if coupon_code is provided.

        Steps (all inside one atomic transaction):
        1. Validate cart is not empty
        2. Validate address belongs to user
        3. Calculate subtotal
        4. Validate and apply coupon (if provided)
        5. Calculate final_amount
        6. Create Order record
        7. Create OrderItem records (price_at_purchase captured now)
        8. Record coupon usage (if coupon applied)
        9. Clear the cart
        10. Mark user as no longer first-time

        Returns:
            Created Order instance

        Raises:
            OrderError: if cart empty, address invalid
            CouponError: if coupon is invalid (re-raised from CouponService)
        """
        # Step 1 — validate cart
        cart_items = CartService.get_cart_items(user=user)
        if not cart_items.exists():
            raise OrderError('Your cart is empty.')

        # Step 2 — validate address
        try:
            address = Address.objects.get(id=address_id, user=user)
        except Address.DoesNotExist:
            raise OrderError('Invalid delivery address.')

        # Step 3 — calculate subtotal
        total_amount = sum(item.shoe.price * item.quantity for item in cart_items)

        # Step 4 — validate coupon if provided
        coupon          = None
        discount_amount = Decimal('0.00')

        if coupon_code:
            from coupons.services import CouponService, CouponError
            coupon          = CouponService.validate(
                code        = coupon_code,
                user        = user,
                order_total = total_amount,
            )
            discount_amount = CouponService.get_discount_amount(coupon, total_amount)

        # Step 5 — final amount
        final_amount = total_amount - discount_amount

        # Step 6 — create Order
        order = Order.objects.create(
            user            = user,
            address         = address,
            status          = Order.Status.PENDING,
            total_amount    = total_amount,
            coupon          = coupon,
            discount_amount = discount_amount,
            final_amount    = final_amount,
        )

        # Step 7 — create OrderItems
        OrderItem.objects.bulk_create([
            OrderItem(
                order             = order,
                shoe              = item.shoe,
                size              = item.size,
                quantity          = item.quantity,
                price_at_purchase = item.shoe.price,
            )
            for item in cart_items
        ])

        # Step 8 — record coupon usage
        if coupon:
            from coupons.services import CouponService
            CouponService.apply_to_order(
                coupon          = coupon,
                user            = user,
                order           = order,
                discount_amount = discount_amount,
            )

        # Step 9 — clear cart
        CartService.clear_cart(user=user)

        # Step 10 — mark first-time user
        try:
            profile = user.profile
            if profile.is_first_time_user:
                profile.is_first_time_user = False
                profile.save(update_fields=['is_first_time_user', 'updated_at'])
        except Exception:
            pass

        logger.info(
            'Order created: id=%s user=%s total=%s discount=%s final=%s coupon=%s',
            order.id, user.username, total_amount,
            discount_amount, final_amount,
            coupon.code if coupon else None,
        )
        return order

    @staticmethod
    @transaction.atomic
    def update_status(order_id: int, new_status: str, updated_by=None) -> Order:
        order   = Order.objects.select_for_update().get(id=order_id)
        allowed = VALID_TRANSITIONS.get(order.status, [])

        if new_status not in allowed:
            raise OrderError(
                f'Cannot transition from "{order.status}" to "{new_status}". '
                f'Allowed: {allowed or "none"}.'
            )

        old_status   = order.status
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        logger.info(
            'Order status: id=%s %s → %s by=%s',
            order.id, old_status, new_status,
            updated_by.username if updated_by else 'system'
        )
        return order

    @staticmethod
    def get_user_orders(user, status=None):
        qs = Order.objects.filter(user=user).select_related(
            'address', 'coupon'
        ).prefetch_related('items__shoe')
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_order_detail(order_id: int, user) -> Order:
        return Order.objects.select_related(
            'address', 'coupon'
        ).prefetch_related(
            'items__shoe'
        ).get(id=order_id, user=user)
