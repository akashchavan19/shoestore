"""
orders/payment_service.py

Razorpay payment integration — all payment logic in one place.

Flow:
  1. create_razorpay_order()   — called when user hits "Pay Now"
                                 creates order on Razorpay's servers
                                 returns order_id for the frontend popup

  2. verify_payment_signature() — called after user completes payment
                                  verifies HMAC-SHA256 signature
                                  CRITICAL: never trust frontend — always verify server-side

  3. confirm_payment()         — called after signature verified
                                 marks our Order as paid in one atomic transaction

  4. handle_webhook()          — called by Razorpay's servers directly
                                 idempotent — safe to call multiple times

Security principles:
- Payment verification uses HMAC-SHA256, not just checking payment_id exists
- Webhook verified using Razorpay signature header
- All DB writes in atomic transactions
- Amount always calculated server-side — never trusted from frontend
- Razorpay amount is in paise (1 INR = 100 paise)
"""

import hmac
import hashlib
import logging
import razorpay

from django.conf import settings
from django.db import transaction

from .models import Order
from .services import OrderService, OrderError

logger = logging.getLogger('onistuka')


class PaymentError(Exception):
    pass


class PaymentService:

    @staticmethod
    def _get_client():
        """
        Returns an authenticated Razorpay client.
        Created fresh each time — stateless, thread-safe.
        """
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    @staticmethod
    def _to_paise(amount_inr) -> int:
        """
        Convert INR decimal to paise integer.
        Razorpay requires amount in smallest currency unit (paise).
        e.g. ₹1499.00 → 149900
        """
        return int(amount_inr * 100)

    @staticmethod
    @transaction.atomic
    def create_razorpay_order(order: Order) -> dict:
        """
        Creates a Razorpay order for payment.

        Called when user clicks "Pay Now" on the payment page.
        Stores the razorpay_order_id on our Order record.

        Args:
            order: Our internal Order instance (status must be PENDING)

        Returns:
            dict with razorpay_order_id, amount, currency, key_id
            — passed to the Razorpay JS checkout popup

        Raises:
            PaymentError: if Razorpay API call fails
            OrderError: if order is not in PENDING status
        """
        if order.status != Order.Status.PENDING:
            raise OrderError(
                f'Cannot initiate payment for order in "{order.status}" status.'
            )

        # If razorpay_order_id already exists, return it
        # (user refreshed the payment page — don't create a duplicate)
        if order.razorpay_order_id:
            return {
                'razorpay_order_id': order.razorpay_order_id,
                'amount':            PaymentService._to_paise(order.final_amount),
                'currency':          'INR',
                'key_id':            settings.RAZORPAY_KEY_ID,
            }

        client = PaymentService._get_client()

        try:
            razorpay_order = client.order.create({
                'amount':          PaymentService._to_paise(order.final_amount),
                'currency':        'INR',
                'receipt':         f'order_{order.id}',
                'notes': {
                    'order_id':    str(order.id),
                    'user_id':     str(order.user.id),
                    'username':    order.user.username,
                },
            })
        except Exception as e:
            logger.error(
                'Razorpay order creation failed: order_id=%s error=%s',
                order.id, str(e)
            )
            raise PaymentError('Payment gateway error. Please try again.')

        # Store razorpay_order_id immediately
        Order.objects.filter(pk=order.pk).update(
            razorpay_order_id=razorpay_order['id']
        )

        logger.info(
            'Razorpay order created: our_order=%s razorpay_order=%s amount=%s',
            order.id, razorpay_order['id'], order.final_amount
        )

        return {
            'razorpay_order_id': razorpay_order['id'],
            'amount':            PaymentService._to_paise(order.final_amount),
            'currency':          'INR',
            'key_id':            settings.RAZORPAY_KEY_ID,
        }

    @staticmethod
    def verify_payment_signature(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> bool:
        """
        Verifies Razorpay payment signature using HMAC-SHA256.

        CRITICAL SECURITY STEP — never skip this.
        Without this, anyone could fake a payment_id and mark orders as paid.

        Razorpay signature = HMAC-SHA256(
            key    = razorpay_key_secret,
            message = razorpay_order_id + '|' + razorpay_payment_id
        )

        Returns:
            True if signature is valid, False otherwise
        """
        message = f'{razorpay_order_id}|{razorpay_payment_id}'

        expected_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(expected_signature, razorpay_signature)

        if not is_valid:
            logger.warning(
                'INVALID payment signature: order=%s payment=%s',
                razorpay_order_id, razorpay_payment_id
            )

        return is_valid

    @staticmethod
    @transaction.atomic
    def confirm_payment(
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Order:
        """
        Confirms payment after signature verification.

        Steps:
        1. Verify signature — reject if invalid
        2. Find our Order by razorpay_order_id
        3. Check it's not already paid (idempotency)
        4. Update Order status to PAID
        5. Store payment_id for future reference/refunds

        Returns:
            Updated Order instance

        Raises:
            PaymentError: if signature invalid or order not found
        """
        # Step 1 — verify signature
        if not PaymentService.verify_payment_signature(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        ):
            raise PaymentError('Payment verification failed. Contact support.')

        # Step 2 — find our order (lock for update to prevent race condition)
        try:
            order = Order.objects.select_for_update().get(
                razorpay_order_id=razorpay_order_id
            )
        except Order.DoesNotExist:
            logger.error(
                'Order not found for razorpay_order_id: %s', razorpay_order_id
            )
            raise PaymentError('Order not found.')

        # Step 3 — idempotency check (webhook may call this twice)
        if order.status == Order.Status.PAID:
            logger.info(
                'Duplicate payment confirmation ignored: order=%s', order.id
            )
            return order

        # Step 4 & 5 — update status and store payment_id
        order.status             = Order.Status.PAID
        order.razorpay_payment_id = razorpay_payment_id
        order.save(update_fields=['status', 'razorpay_payment_id', 'updated_at'])

        logger.info(
            'Payment confirmed: order=%s user=%s amount=%s payment_id=%s',
            order.id, order.user.username, order.final_amount, razorpay_payment_id
        )

        # Fire confirmation email async — does not block the response
        try:
            from orders.tasks import send_order_confirmation_email_task
            send_order_confirmation_email_task.delay(order.id)
        except Exception:
            # Celery not running — send synchronously as fallback
            try:
                from orders.tasks import send_order_confirmation_email
                send_order_confirmation_email(order.id)
            except Exception as email_err:
                logger.error('Could not send confirmation email: %s', email_err)

        return order

    @staticmethod
    def handle_webhook(payload: bytes, webhook_signature: str) -> bool:
        """
        Handles Razorpay webhook events.

        Razorpay calls this endpoint directly when payment status changes.
        This is the backup confirmation in case the user closes the browser
        before the frontend can confirm the payment.

        Webhook secret must be set in Razorpay dashboard and in .env.

        Returns:
            True if webhook was valid and processed
            False if webhook signature invalid
        """
        webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
        if not webhook_secret:
            logger.warning('RAZORPAY_WEBHOOK_SECRET not set — webhook not verified.')
            return False

        client = PaymentService._get_client()

        try:
            client.utility.verify_webhook_signature(
                payload.decode('utf-8'),
                webhook_signature,
                webhook_secret,
            )
        except Exception:
            logger.warning('Invalid webhook signature received.')
            return False

        import json
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            return False

        event_type = event.get('event')
        logger.info('Razorpay webhook received: %s', event_type)

        if event_type == 'payment.captured':
            payment = event.get('payload', {}).get('payment', {}).get('entity', {})
            razorpay_order_id  = payment.get('order_id', '')
            razorpay_payment_id = payment.get('id', '')

            if razorpay_order_id and razorpay_payment_id:
                try:
                    # Webhook doesn't have signature to verify (it's already verified above)
                    # So we directly confirm if order exists and is still pending
                    order = Order.objects.filter(
                        razorpay_order_id=razorpay_order_id,
                        status=Order.Status.PENDING,
                    ).first()

                    if order:
                        order.status              = Order.Status.PAID
                        order.razorpay_payment_id = razorpay_payment_id
                        order.save(update_fields=['status', 'razorpay_payment_id', 'updated_at'])
                        logger.info(
                            'Order marked PAID via webhook: order=%s', order.id
                        )
                except Exception as e:
                    logger.error('Webhook processing error: %s', str(e))

        return True
