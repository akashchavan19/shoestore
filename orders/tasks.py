"""
orders/tasks.py

Celery async tasks for order processing.

Why async tasks here?
- Sending emails blocks the request for 1-3 seconds
- With Celery, the view returns instantly and email sends in background
- If email fails, Celery retries automatically (up to CELERY_TASK_MAX_RETRIES)
- User never sees a slow checkout because of email server issues

Tasks defined here:
- send_order_confirmation_email — fired after successful payment
- send_payment_failed_email     — fired when payment fails
"""

import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger('onistuka')


def get_celery_app():
    from onistuka.celery import app
    return app


def send_order_confirmation_email(order_id: int):
    """
    Sends order confirmation email.
    Called after PaymentService.confirm_payment() succeeds.

    Runs synchronously if Celery is not running (dev mode).
    Runs as background task if Celery worker is active (prod mode).
    """
    try:
        from .models import Order
        order = Order.objects.select_related(
            'user', 'address'
        ).prefetch_related('items__shoe').get(id=order_id)

        subject = f'Order Confirmed — #{order.id} | Onistuka'
        message = (
            f'Hi {order.user.first_name or order.user.username},\n\n'
            f'Your order #{order.id} has been confirmed!\n\n'
            f'Order Total: ₹{order.final_amount}\n'
            f'Delivery to: {order.address.get_full_address()}\n\n'
            f'We will notify you once your order is shipped.\n\n'
            f'Thank you for shopping with Onistuka!'
        )

        send_mail(
            subject      = subject,
            message      = message,
            from_email   = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [order.user.email],
            fail_silently = False,
        )

        logger.info(
            'Order confirmation email sent: order=%s user=%s email=%s',
            order.id, order.user.username, order.user.email
        )

    except Exception as e:
        logger.error('Failed to send order confirmation email: order=%s error=%s', order_id, str(e))
        raise


# Register as Celery task if Celery is available
try:
    app = get_celery_app()

    @app.task(
        bind=True,
        max_retries=3,
        default_retry_delay=60,  # retry after 60 seconds
        name='orders.send_order_confirmation_email',
    )
    def send_order_confirmation_email_task(self, order_id: int):
        try:
            send_order_confirmation_email(order_id)
        except Exception as exc:
            logger.warning('Retrying order confirmation email: order=%s attempt=%s', order_id, self.request.retries)
            raise self.retry(exc=exc)

except Exception:
    # Celery not available — tasks will run synchronously
    pass
