"""
coupons/views.py

Coupon validation endpoint — called via AJAX from cart page.
Returns JSON so the cart page can show discount preview without page reload.
"""

import logging
from decimal import Decimal, InvalidOperation
from django.views import View
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin

from .services import CouponService, CouponError

logger = logging.getLogger('onistuka')


class ValidateCouponView(LoginRequiredMixin, View):
    """
    POST /coupons/validate/
    Body: { coupon_code, order_total }
    Returns: { valid, discount_amount, message, coupon_description }
    """

    def post(self, request):
        coupon_code = request.POST.get('coupon_code', '').strip()
        order_total_raw = request.POST.get('order_total', '0')

        if not coupon_code:
            return JsonResponse({'valid': False, 'message': 'Please enter a coupon code.'})

        try:
            order_total = Decimal(order_total_raw)
        except InvalidOperation:
            return JsonResponse({'valid': False, 'message': 'Invalid order total.'})

        try:
            coupon          = CouponService.validate(
                code        = coupon_code,
                user        = request.user,
                order_total = order_total,
            )
            discount_amount = CouponService.get_discount_amount(coupon, order_total)
            final_amount    = order_total - discount_amount

            return JsonResponse({
                'valid':               True,
                'coupon_code':         coupon.code,
                'discount_amount':     str(discount_amount),
                'final_amount':        str(final_amount),
                'description':         coupon.description,
                'message':             f'Coupon applied! You save ₹{discount_amount}',
            })

        except CouponError as e:
            return JsonResponse({'valid': False, 'message': str(e)})
