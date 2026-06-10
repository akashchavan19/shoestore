"""
wishlist/models.py

Design decisions:
- OneWishlistItem per (user + shoe) — DB constraint enforced
- No session-based wishlist — wishlist requires login (makes sense UX-wise)
- added_at for ordering by most recently wishlisted
- DB index on user for fast per-user lookups
"""

from django.db import models
from django.contrib.auth.models import User
from products.models import Shoe


class WishlistItem(models.Model):
    """
    A single shoe saved to a user's wishlist.
    One entry per user+shoe combination — enforced at DB level.
    """
    user     = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
    )
    shoe     = models.ForeignKey(
        Shoe,
        on_delete=models.CASCADE,
        related_name='wishlisted_by',
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # One shoe per user in wishlist — enforced at DB level
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'shoe'],
                name='unique_user_wishlist_item',
            )
        ]
        indexes  = [models.Index(fields=['user'])]
        ordering = ['-added_at']

    def __str__(self):
        return f'{self.user.username} → {self.shoe.name}'
