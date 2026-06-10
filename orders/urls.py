from django.urls import path
from .views import (
    SelectAddressView,
    PaymentView,
    PaymentCallbackView,
    RazorpayWebhookView,
    OrderSuccessView,
    OrderHistoryView,
    OrderDetailView,
)

urlpatterns = [
    path('select-address/',          SelectAddressView.as_view(),   name='select-address'),
    path('payment/<int:order_id>/',  PaymentView.as_view(),         name='payment'),
    path('payment-callback/',        PaymentCallbackView.as_view(), name='payment-callback'),
    path('webhook/razorpay/',        RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    path('success/<int:order_id>/',  OrderSuccessView.as_view(),    name='order-success'),
    path('history/',                 OrderHistoryView.as_view(),     name='order-history'),
    path('<int:order_id>/',          OrderDetailView.as_view(),      name='order-detail'),
]
