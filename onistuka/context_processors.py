"""
onistuka/context_processors.py

Global template context processors.
These inject data into EVERY template automatically.

cart_count:
- Shows cart item count in navbar without a separate DB query on every page
- Uses cache with 2-minute TTL — fast enough for accuracy, cheap on DB
- Anonymous users get count from session cart
- Authenticated users get count from user cart
"""

import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger('onistuka')


def cart_count(request):
    """
    Injects {{ cart_count }} into every template.
    Cached per user/session to avoid a DB hit on every page load.
    """
    try:
        if request.user.is_authenticated:
            cache_key = f'cart_count_user_{request.user.id}'
        else:
            session_key = request.session.session_key
            if not session_key:
                return {'cart_count': 0}
            cache_key = f'cart_count_session_{session_key}'

        count = cache.get(cache_key)

        if count is None:
            from cart.models import CartItem
            from django.db.models import Sum

            if request.user.is_authenticated:
                result = CartItem.objects.filter(
                    user=request.user
                ).aggregate(total=Sum('quantity'))
            else:
                result = CartItem.objects.filter(
                    session_key=session_key,
                    user__isnull=True,
                ).aggregate(total=Sum('quantity'))

            count = result['total'] or 0
            cache.set(cache_key, count, settings.CACHE_TTL['CART_COUNT'])

    except Exception:
        # Never crash a page because of cart count
        count = 0

    return {'cart_count': count}
