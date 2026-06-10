from django.urls import path
from .views import CartView, AddToCartView, RemoveFromCartView, AddAddressView

urlpatterns = [
    path('',                  CartView.as_view(),           name='view-cart'),
    path('add/<int:shoe_id>/', AddToCartView.as_view(),      name='add-to-cart'),
    path('remove/<int:item_id>/', RemoveFromCartView.as_view(), name='remove-from-cart'),
    path('add-address/',      AddAddressView.as_view(),      name='add-address'),
]
