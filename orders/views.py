"""
orders/views.py — Updated for Phase 4 with coupon support.
"""
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Order
from .services import OrderService, OrderError
from .payment_service import PaymentService, PaymentError
from cart.models import Address
from cart.services import CartService
from coupons.services import CouponError

logger = logging.getLogger('onistuka')


class SelectAddressView(LoginRequiredMixin, View):
    template_name = 'orders/select_address.html'

    def get(self, request):
        summary = CartService.get_cart_summary(user=request.user)
        if not summary['items']:
            messages.info(request, 'Your cart is empty.')
            return redirect('view-cart')
        return render(request, self.template_name, {
            'addresses':  Address.objects.filter(user=request.user),
            'cart_items': summary['items'],
            'total':      summary['total'],
        })

    def post(self, request):
        address_id  = request.POST.get('address_id')
        coupon_code = request.POST.get('coupon_code', '').strip()

        if not address_id:
            messages.error(request, 'Please select a delivery address.')
            return redirect('select-address')

        try:
            order = OrderService.create_order_from_cart(
                user        = request.user,
                address_id  = int(address_id),
                coupon_code = coupon_code,
            )
            return redirect('payment', order_id=order.id)

        except (OrderError, CouponError) as e:
            messages.error(request, str(e))
            return redirect('select-address')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid selection. Please try again.')
            return redirect('select-address')


class PaymentView(LoginRequiredMixin, View):
    template_name = 'orders/payment.html'

    def get(self, request, order_id):
        try:
            order = OrderService.get_order_detail(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('view-cart')

        if order.status != Order.Status.PENDING:
            if order.status == Order.Status.PAID:
                return redirect('order-success', order_id=order.id)
            messages.error(request, f'This order cannot be paid (status: {order.status}).')
            return redirect('order-history')

        try:
            payment_data = PaymentService.create_razorpay_order(order)
        except PaymentError as e:
            messages.error(request, str(e))
            return redirect('order-history')

        return render(request, self.template_name, {
            'order':        order,
            'payment_data': payment_data,
            'callback_url': request.build_absolute_uri('/orders/payment-callback/'),
            'user_name':    request.user.get_full_name() or request.user.username,
            'user_email':   request.user.email,
        })


class PaymentCallbackView(LoginRequiredMixin, View):
    def post(self, request):
        razorpay_order_id   = request.POST.get('razorpay_order_id', '')
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_signature  = request.POST.get('razorpay_signature', '')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            messages.error(request, 'Payment was not completed. Please try again.')
            return redirect('order-history')

        try:
            order = PaymentService.confirm_payment(
                razorpay_order_id   = razorpay_order_id,
                razorpay_payment_id = razorpay_payment_id,
                razorpay_signature  = razorpay_signature,
            )
            messages.success(request, 'Payment successful! Your order is confirmed.')
            return redirect('order-success', order_id=order.id)
        except PaymentError as e:
            messages.error(request, str(e))
            return redirect('order-history')


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(View):
    def post(self, request):
        webhook_signature = request.headers.get('X-Razorpay-Signature', '')
        success = PaymentService.handle_webhook(
            payload=request.body,
            webhook_signature=webhook_signature,
        )
        return HttpResponse(status=200 if success else 400)


class OrderSuccessView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        try:
            order = OrderService.get_order_detail(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('home')
        return render(request, 'orders/order_success.html', {'order': order})


class OrderHistoryView(LoginRequiredMixin, ListView):
    template_name       = 'orders/order_history.html'
    context_object_name = 'orders'
    paginate_by         = 10

    def get_queryset(self):
        return OrderService.get_user_orders(user=self.request.user)


class OrderDetailView(LoginRequiredMixin, View):
    def get(self, request, order_id):
        try:
            order = OrderService.get_order_detail(order_id=order_id, user=request.user)
        except Order.DoesNotExist:
            messages.error(request, 'Order not found.')
            return redirect('order-history')
        return render(request, 'orders/order_detail.html', {'order': order})
