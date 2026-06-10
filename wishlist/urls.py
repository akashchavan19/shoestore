from django.urls import path
from .views import WishlistView, WishlistToggleView, WishlistMoveToCartView, WishlistRemoveView

urlpatterns = [
    path('',                          WishlistView.as_view(),          name='wishlist'),
    path('toggle/<int:shoe_id>/',     WishlistToggleView.as_view(),    name='wishlist-toggle'),
    path('move-to-cart/<int:item_id>/', WishlistMoveToCartView.as_view(), name='wishlist-move-to-cart'),
    path('remove/<int:item_id>/',     WishlistRemoveView.as_view(),    name='wishlist-remove'),
]
