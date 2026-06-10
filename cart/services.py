"""
cart/services.py

All cart business logic lives here.
Views call these methods — they never manipulate CartItem directly.

Key design: Cart merging on login
When an anonymous user logs in, their session cart is merged into
their user cart. This is the most important operation in this service.

Principles:
- Atomic transactions on all writes
- N+1 safe — querysets use select_related where needed
- Cart identified by user (logged in) or session_key (anonymous)
- All qty changes go through a single method — no scattered .save() calls
"""

import logging
from django.db import transaction
from django.db.models import F
from .models import CartItem

logger = logging.getLogger('onistuka')


class CartService:

    # -----------------------------------------------------------------------
    # Helpers — identify the cart owner
    # -----------------------------------------------------------------------

    @staticmethod
    def _get_cart_queryset(user=None, session_key=None):
        """
        Returns the queryset for the correct cart.
        Logged-in users use user-linked cart; anonymous use session cart.
        Always select_related shoe to avoid N+1 in templates.
        """
        if user and user.is_authenticated:
            return CartItem.objects.filter(user=user).select_related('shoe')
        if session_key:
            return CartItem.objects.filter(session_key=session_key, user__isnull=True).select_related('shoe')
        return CartItem.objects.none()

    # -----------------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------------

    @staticmethod
    def get_cart_items(user=None, session_key=None):
        """Returns all cart items for this user or session."""
        return CartService._get_cart_queryset(user=user, session_key=session_key)

    @staticmethod
    def get_cart_summary(user=None, session_key=None):
        """
        Returns { items, total, item_count } in one call.
        Templates use this instead of computing totals themselves.
        """
        items = CartService.get_cart_items(user=user, session_key=session_key)
        total      = sum(item.subtotal for item in items)
        item_count = sum(item.quantity  for item in items)
        return {
            'items':      items,
            'total':      total,
            'item_count': item_count,
        }

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def add_item(shoe, size: str, quantity: int = 1, user=None, session_key=None):
        """
        Adds a shoe to the cart or increments quantity if already present.

        Args:
            shoe:        Shoe instance
            size:        Selected size string
            quantity:    How many to add (default 1)
            user:        Logged-in User instance (or None)
            session_key: Session key string (or None)

        Returns:
            (CartItem, created: bool)
        """
        if not size:
            raise ValueError('A size must be selected before adding to cart.')
        if quantity < 1:
            raise ValueError('Quantity must be at least 1.')

        lookup = {'shoe': shoe, 'size': size}
        if user and user.is_authenticated:
            lookup['user'] = user
        else:
            lookup['session_key'] = session_key
            lookup['user']        = None

        item, created = CartItem.objects.get_or_create(
            **lookup,
            defaults={'quantity': quantity},
        )

        if not created:
            # Use F() to avoid race condition: read-modify-write
            CartItem.objects.filter(pk=item.pk).update(quantity=F('quantity') + quantity)
            item.refresh_from_db()

        logger.debug(
            'Cart add: shoe=%s size=%s qty=%s user=%s session=%s created=%s',
            shoe.id, size, quantity,
            user.id if user and user.is_authenticated else None,
            session_key, created
        )
        CartService._invalidate_cart_count_cache(user=user, session_key=session_key)
        return item, created

    @staticmethod
    @transaction.atomic
    def remove_item(item_id: int, user=None, session_key=None):
        """
        Removes a cart item. Verifies ownership before deleting.

        Raises:
            CartItem.DoesNotExist: if item not found or doesn't belong to this cart
        """
        qs = CartService._get_cart_queryset(user=user, session_key=session_key)
        item = qs.get(pk=item_id)   # raises DoesNotExist if not owned by this cart
        item.delete()
        CartService._invalidate_cart_count_cache(user=user, session_key=session_key)
        logger.debug('Cart remove: item_id=%s', item_id)

    @staticmethod
    @transaction.atomic
    def update_quantity(item_id: int, quantity: int, user=None, session_key=None):
        """
        Sets quantity for a cart item. Removes item if quantity <= 0.

        Returns:
            Updated CartItem or None if deleted
        """
        qs   = CartService._get_cart_queryset(user=user, session_key=session_key)
        item = qs.get(pk=item_id)

        if quantity <= 0:
            item.delete()
            return None

        item.quantity = quantity
        item.save(update_fields=['quantity', 'updated_at'])
        return item

    @staticmethod
    @transaction.atomic
    def clear_cart(user=None, session_key=None):
        """Removes all items from this cart. Used after order is placed."""
        CartService._get_cart_queryset(user=user, session_key=session_key).delete()
        logger.debug(
            'Cart cleared: user=%s session=%s',
            user.id if user and user.is_authenticated else None,
            session_key
        )

    # -----------------------------------------------------------------------
    # Merge — called on login
    # -----------------------------------------------------------------------

    @staticmethod
    def _invalidate_cart_count_cache(user=None, session_key=None):
        """Clears cached cart count so navbar updates immediately."""
        from django.core.cache import cache
        try:
            if user and user.is_authenticated:
                cache.delete(f'cart_count_user_{user.id}')
            elif session_key:
                cache.delete(f'cart_count_session_{session_key}')
        except Exception:
            pass

    @staticmethod
    @transaction.atomic
    def merge_session_cart_into_user(user, session_key: str):
        """
        Called when an anonymous user logs in.
        Moves all session cart items to the user's cart.

        Merge strategy:
        - If user already has the same shoe+size → add quantities together
        - If user doesn't have it → re-assign the session item to the user

        This ensures nothing is lost when logging in mid-browse.
        """
        if not session_key:
            return

        session_items = CartItem.objects.filter(
            session_key=session_key,
            user__isnull=True,
        ).select_related('shoe')

        if not session_items.exists():
            return

        for session_item in session_items:
            existing = CartItem.objects.filter(
                user=user,
                shoe=session_item.shoe,
                size=session_item.size,
            ).first()

            if existing:
                # Add quantities
                CartItem.objects.filter(pk=existing.pk).update(
                    quantity=F('quantity') + session_item.quantity
                )
                session_item.delete()
            else:
                # Re-assign to user
                session_item.user        = user
                session_item.session_key = None
                session_item.save(update_fields=['user', 'session_key', 'updated_at'])

        logger.info(
            'Cart merged: session=%s → user=%s (id=%s)',
            session_key, user.username, user.id
        )
