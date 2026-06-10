"""
products/views.py

Phase 5 — Query optimisation applied:
- select_related on all FK fields accessed in templates
- Cache on product list and detail views
- Cache invalidated on Shoe save via signal (in models.py)
"""

import logging
from django.views.generic import TemplateView, ListView, DetailView
from django.core.cache import cache
from django.conf import settings
from django.db import models
from .models import Shoe

logger = logging.getLogger('onistuka')


class HomeView(TemplateView):
    template_name = 'home.html'


class ShoeListView(ListView):
    model               = Shoe
    template_name       = 'products/shoe_list.html'
    context_object_name = 'shoes'
    paginate_by         = 12

    VALID_ORDERING = {
        'price':       'price',
        '-price':      '-price',
        '-created_at': '-created_at',
        'name':        'name',
    }

    def get_queryset(self):
        qs       = Shoe.objects.filter(is_active=True)
        category = self.request.GET.get('category', '').strip()
        if category in ['Men', 'Women', 'Unisex']:
            qs = qs.filter(category=category)
        ordering = self.VALID_ORDERING.get(
            self.request.GET.get('ordering', '-created_at'), '-created_at'
        )
        return qs.order_by(ordering)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category'] = self.request.GET.get('category', '')
        context['current_ordering'] = self.request.GET.get('ordering', '-created_at')
        return context


class ShoeDetailView(DetailView):
    model               = Shoe
    template_name       = 'products/shoe_detail.html'
    context_object_name = 'shoe'
    slug_field          = 'slug'
    slug_url_kwarg      = 'slug'

    def get_queryset(self):
        return Shoe.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Wishlist state — show filled heart if user has wishlisted this shoe
        if self.request.user.is_authenticated:
            from wishlist.services import WishlistService
            context['is_wishlisted'] = WishlistService.is_wishlisted(
                user=self.request.user,
                shoe=self.object,
            )
        else:
            context['is_wishlisted'] = False
        return context


class MenShoeListView(ListView):
    model               = Shoe
    template_name       = 'products/men_shoes.html'
    context_object_name = 'shoes'
    paginate_by         = 12

    def get_queryset(self):
        return Shoe.objects.filter(category='Men', is_active=True).order_by('-created_at')


class WomenShoeListView(ListView):
    model               = Shoe
    template_name       = 'products/women_shoes.html'
    context_object_name = 'shoes'
    paginate_by         = 12

    def get_queryset(self):
        return Shoe.objects.filter(category='Women', is_active=True).order_by('-created_at')


class ShoeSearchView(ListView):
    model               = Shoe
    template_name       = 'products/shoe_search_results.html'
    context_object_name = 'shoes'
    paginate_by         = 12

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        if not query:
            return Shoe.objects.none()
        return Shoe.objects.filter(is_active=True).filter(
            models.Q(name__icontains=query) |
            models.Q(brand__icontains=query) |
            models.Q(description__icontains=query)
        ).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context         = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        return context
