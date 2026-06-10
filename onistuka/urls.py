"""
Root URL configuration for Onistuka.

URL layout:
  /                      → products (home + listing pages)
  /api/v1/               → REST API (JWT auth, DRF)
  /accounts/             → session-based auth views (login/register pages)
  /cart/                 → cart pages
  /orders/               → order pages
  /admin/                → Django admin
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ---------------------------------------------------------------------------
# API v1 routes — all REST endpoints live under /api/v1/
# Each app will expose its own api_urls.py
# ---------------------------------------------------------------------------
api_v1_patterns = [
    path('auth/', include('accounts.api_urls')),
    path('products/', include('products.api_urls')),
    path('cart/', include('cart.api_urls')),
    path('orders/', include('orders.api_urls')),
]

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # REST API
    path('api/v1/', include(api_v1_patterns)),

    # Template-rendered pages (kept for the existing frontend)
    path('', include('products.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('accounts.urls')),
    path('wishlist/', include('wishlist.urls')),
    path('coupons/', include('coupons.urls')),
]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ---------------------------------------------------------------------------
# Custom error handlers
# ---------------------------------------------------------------------------
handler400 = 'onistuka.views.bad_request'
handler403 = 'onistuka.views.permission_denied'
handler404 = 'onistuka.views.page_not_found'
handler500 = 'onistuka.views.server_error'
