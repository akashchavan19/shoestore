"""
cart/views.py

Template-rendered cart views.
All business logic delegated to CartService.
Views only: get session/user context, call service, render template.
"""

import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView

from .models import CartItem, Address
from .forms import AddressForm
from .services import CartService
from products.models import Shoe

logger = logging.getLogger('onistuka')


def _cart_owner(request):
    """Returns (user, session_key) tuple for CartService calls."""
    if request.user.is_authenticated:
        return request.user, None
    if not request.session.session_key:
        request.session.create()
    return None, request.session.session_key


class CartView(ListView):
    """GET /cart/ — displays the cart."""
    template_name      = 'cart/cart.html'
    context_object_name = 'cart_items'

    def get_queryset(self):
        user, session_key = _cart_owner(self.request)
        return CartService.get_cart_items(user=user, session_key=session_key)

    def get_context_data(self, **kwargs):
        context   = super().get_context_data(**kwargs)
        user, session_key = _cart_owner(self.request)
        summary   = CartService.get_cart_summary(user=user, session_key=session_key)
        context['total']      = summary['total']
        context['item_count'] = summary['item_count']
        return context


class AddToCartView(View):
    """
    POST /cart/add/<shoe_id>/
    GET  /cart/add/<shoe_id>/  → redirect to detail page (graceful fallback)
    """

    def post(self, request, shoe_id):
        shoe = get_object_or_404(Shoe, id=shoe_id, is_active=True)
        size = request.POST.get('size', '').strip()
        user, session_key = _cart_owner(request)

        try:
            quantity = int(request.POST.get('quantity', 1))
            quantity = max(1, min(quantity, 10))   # clamp between 1 and 10
        except (ValueError, TypeError):
            quantity = 1

        try:
            CartService.add_item(
                shoe        = shoe,
                size        = size,
                quantity    = quantity,
                user        = user,
                session_key = session_key,
            )
            messages.success(request, f'"{shoe.name}" added to your cart.')
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('view-cart')

    def get(self, request, shoe_id):
        shoe = get_object_or_404(Shoe, id=shoe_id, is_active=True)
        return redirect('shoe-detail', slug=shoe.slug)


class RemoveFromCartView(View):
    """POST /cart/remove/<item_id>/"""

    def post(self, request, item_id):
        user, session_key = _cart_owner(request)
        try:
            CartService.remove_item(item_id=item_id, user=user, session_key=session_key)
            messages.success(request, 'Item removed from cart.')
        except CartItem.DoesNotExist:
            messages.error(request, 'Item not found in your cart.')
        return redirect('view-cart')


class AddAddressView(LoginRequiredMixin, CreateView):
    """GET/POST /cart/add-address/"""
    model         = Address
    form_class    = AddressForm
    template_name = 'cart/add_address.html'
    success_url   = reverse_lazy('select-address')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Address saved successfully.')
        return super().form_valid(form)
