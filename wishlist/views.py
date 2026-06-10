"""
wishlist/views.py — thin views, all logic in WishlistService.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

from .models import WishlistItem
from .services import WishlistService
from products.models import Shoe

logger = logging.getLogger('onistuka')


class WishlistView(LoginRequiredMixin, View):
    """GET /wishlist/ — show all wishlisted shoes."""

    def get(self, request):
        items = WishlistService.get_wishlist(user=request.user)
        return render(request, 'wishlist/wishlist.html', {'items': items})


class WishlistToggleView(LoginRequiredMixin, View):
    """
    POST /wishlist/toggle/<shoe_id>/
    Adds or removes a shoe from wishlist.
    Returns JSON for AJAX calls, redirects for regular form submits.
    """

    def post(self, request, shoe_id):
        shoe  = get_object_or_404(Shoe, id=shoe_id, is_active=True)
        added = WishlistService.toggle(user=request.user, shoe=shoe)

        # AJAX request — return JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'added':   added,
                'message': f'Added to wishlist' if added else 'Removed from wishlist',
            })

        # Regular form submit — redirect back
        if added:
            messages.success(request, f'"{shoe.name}" added to your wishlist.')
        else:
            messages.info(request, f'"{shoe.name}" removed from your wishlist.')

        # Go back to where the user came from
        return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


class WishlistMoveToCartView(LoginRequiredMixin, View):
    """POST /wishlist/move-to-cart/<item_id>/ — move item to cart."""

    def post(self, request, item_id):
        size = request.POST.get('size', '').strip()

        if not size:
            messages.error(request, 'Please select a size before adding to cart.')
            return redirect('wishlist')

        try:
            WishlistService.move_to_cart(
                user             = request.user,
                wishlist_item_id = item_id,
                size             = size,
            )
            messages.success(request, 'Item moved to your cart.')
        except WishlistItem.DoesNotExist:
            messages.error(request, 'Wishlist item not found.')
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('wishlist')


class WishlistRemoveView(LoginRequiredMixin, View):
    """POST /wishlist/remove/<item_id>/"""

    def post(self, request, item_id):
        try:
            item = WishlistItem.objects.get(id=item_id, user=request.user)
            item.delete()
            messages.info(request, 'Removed from wishlist.')
        except WishlistItem.DoesNotExist:
            messages.error(request, 'Item not found.')
        return redirect('wishlist')
