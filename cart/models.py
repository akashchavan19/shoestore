"""
cart/models.py

Cart design:
- CartItem is linked to BOTH session_key (anonymous) AND user (logged in)
- On login, anonymous cart items are merged into the user's cart
- This is handled by the cart service, not the model
- Address moved here from original — it belongs with cart/checkout

Design decisions:
- session_key nullable — not needed once user is linked
- user nullable — allows anonymous shopping
- size stored on CartItem — not just on the shoe (user picks a size)
- DB index on (session_key, shoe) and (user, shoe) for fast cart lookups
- unique_together prevents duplicate cart entries for the same shoe+size
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from products.models import Shoe


class CartItem(models.Model):
    """
    A single item in a user's or session's cart.
    One CartItem per (user/session + shoe + size) combination.
    """
    # Either user or session_key will be set — not necessarily both
    user        = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='cart_items',
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    shoe        = models.ForeignKey(Shoe, on_delete=models.CASCADE, related_name='cart_items')
    size        = models.CharField(max_length=10, blank=True)
    quantity    = models.PositiveIntegerField(default=1)
    added_at    = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        # Prevent duplicate entries: same user + same shoe + same size = one row
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'shoe', 'size'],
                condition=models.Q(user__isnull=False),
                name='unique_user_cart_item',
            ),
            models.UniqueConstraint(
                fields=['session_key', 'shoe', 'size'],
                condition=models.Q(session_key__isnull=False),
                name='unique_session_cart_item',
            ),
        ]
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['user']),
        ]
        ordering = ['added_at']

    def __str__(self):
        owner = self.user.username if self.user else f'session:{self.session_key[:8]}'
        return f'{self.shoe.name} (size {self.size}) x{self.quantity} — {owner}'

    @property
    def subtotal(self):
        """Price for this line item."""
        return self.shoe.price * self.quantity


class Address(models.Model):
    """
    Saved delivery address for a user.
    Users can have multiple addresses; one is selected at checkout.
    """
    pincode_validator = RegexValidator(
        regex=r'^\d{6}$',
        message='PIN code must be exactly 6 digits.'
    )
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Enter a valid phone number.'
    )

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    full_name   = models.CharField(max_length=100, help_text='Name of the recipient.')
    phone       = models.CharField(max_length=15, validators=[phone_validator])
    house_no    = models.CharField(max_length=50)
    street      = models.CharField(max_length=200)
    city        = models.CharField(max_length=100)
    state       = models.CharField(max_length=100)
    pincode     = models.CharField(max_length=6, validators=[pincode_validator])
    is_default  = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f'{self.full_name} — {self.house_no}, {self.city} {self.pincode}'

    def get_full_address(self):
        return f'{self.house_no}, {self.street}, {self.city}, {self.state} — {self.pincode}'
