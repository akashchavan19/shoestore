"""
wishlist/services.py

All wishlist business logic in one place.
Views call these — never manipulate WishlistItem directly.

Principles:
- Atomic transactions on all writes
- Toggle pattern — add if not present, remove if present
- Move-to-cart is atomic — wishlist remove + cart add in one transaction
- N+1 safe querysets
"""

import logging
from django.db import transaction
from .models import WishlistItem
from cart.services import CartService

logger = logging.getLogger('onistuka')


class WishlistService:

    @staticmethod
    def get_wishlist(user):
        """
        Returns all wishlist items for a user.
        select_related shoe to avoid N+1 in templates.
        """
        return WishlistItem.objects.filter(
            user=user
        ).select_related('shoe')

    @staticmethod
    def get_wishlist_shoe_ids(user) -> set:
        """
        Returns a set of shoe IDs in the user's wishlist.
        Used in product listing templates to show filled/empty heart icons
        without N+1 queries.
        """
        return set(
            WishlistItem.objects.filter(user=user).values_list('shoe_id', flat=True)
        )

    @staticmethod
    @transaction.atomic
    def toggle(user, shoe) -> bool:
        """
        Adds shoe to wishlist if not present, removes it if present.

        Returns:
            True  — shoe was added
            False — shoe was removed
        """
        item = WishlistItem.objects.filter(user=user, shoe=shoe).first()

        if item:
            item.delete()
            logger.debug('Wishlist remove: user=%s shoe=%s', user.id, shoe.id)
            return False
        else:
            WishlistItem.objects.create(user=user, shoe=shoe)
            logger.debug('Wishlist add: user=%s shoe=%s', user.id, shoe.id)
            return True

    @staticmethod
    @transaction.atomic
    def move_to_cart(user, wishlist_item_id: int, size: str):
        """
        Moves a wishlist item to the cart atomically.
        Removes from wishlist AND adds to cart in one transaction.
        If cart add fails, wishlist item is NOT removed (rollback).

        Args:
            user:             The user performing the action
            wishlist_item_id: WishlistItem pk
            size:             Size selected by user (required for cart)

        Raises:
            WishlistItem.DoesNotExist: if item not found or not owned by user
            ValueError: if no size selected
        """
        item = WishlistItem.objects.select_related('shoe').get(
            id=wishlist_item_id,
            user=user,
        )

        # Add to cart first — if this fails, wishlist item stays (atomic rollback)
        CartService.add_item(
            shoe=item.shoe,
            size=size,
            quantity=1,
            user=user,
        )

        # Only remove from wishlist after cart add succeeds
        item.delete()

        logger.info(
            'Wishlist → Cart: user=%s shoe=%s size=%s',
            user.id, item.shoe.id, size
        )

    @staticmethod
    def is_wishlisted(user, shoe) -> bool:
        """Check if a specific shoe is in the user's wishlist."""
        if not user.is_authenticated:
            return False
        return WishlistItem.objects.filter(user=user, shoe=shoe).exists()
