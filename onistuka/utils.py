"""
onistuka/utils.py

Project-wide utilities.
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger('onistuka')


def custom_exception_handler(exc, context):
    """
    Returns all DRF errors in a consistent shape:

        {
            "success": false,
            "error": {
                "code": "authentication_failed",
                "message": "...",
                "details": { ... }   # only present when extra info exists
            }
        }

    Falls back to DRF's default handler for anything it doesn't recognise.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            'success': False,
            'error': {
                'code': _get_error_code(response),
                'message': _get_error_message(response),
            }
        }

        # Keep field-level validation details if present
        if isinstance(response.data, dict):
            details = {k: v for k, v in response.data.items()
                       if k not in ('detail', 'code')}
            if details:
                error_payload['error']['details'] = details

        response.data = error_payload

    else:
        # Unhandled exception — log it and return 500
        logger.exception('Unhandled exception in view: %s', exc)
        response = Response(
            {
                'success': False,
                'error': {
                    'code': 'internal_server_error',
                    'message': 'An unexpected error occurred. Please try again later.',
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _get_error_code(response) -> str:
    """Extract a machine-readable error code from the DRF response."""
    if isinstance(response.data, dict):
        code = response.data.get('code')
        if code:
            return str(code)
    return _status_to_code(response.status_code)


def _get_error_message(response) -> str:
    """Extract a human-readable message from the DRF response."""
    if isinstance(response.data, dict):
        detail = response.data.get('detail')
        if detail:
            return str(detail)
        # Flatten field errors into one string for the top-level message
        msgs = []
        for key, val in response.data.items():
            if key in ('code',):
                continue
            if isinstance(val, list):
                msgs.extend([str(v) for v in val])
            else:
                msgs.append(str(val))
        if msgs:
            return ' '.join(msgs)
    return 'An error occurred.'


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: 'bad_request',
        401: 'authentication_failed',
        403: 'permission_denied',
        404: 'not_found',
        405: 'method_not_allowed',
        429: 'too_many_requests',
        500: 'internal_server_error',
    }
    return mapping.get(status_code, 'error')
