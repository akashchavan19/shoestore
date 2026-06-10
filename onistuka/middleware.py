"""
onistuka/middleware.py

Custom middleware for Phase 5.

RequestTimingMiddleware:
- Measures response time for every request
- Logs any request that takes longer than SLOW_REQUEST_THRESHOLD_MS
- In prod this catches N+1 queries and slow views before users complain
"""

import time
import logging

logger = logging.getLogger('onistuka')

# Log any request slower than this (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 500


class RequestTimingMiddleware:
    """
    Measures request processing time.
    Logs slow requests (> 500ms) as warnings so they're visible in prod logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000

        # Always attach timing to response header (visible in browser devtools)
        response['X-Response-Time'] = f'{duration_ms:.1f}ms'

        # Log slow requests as warnings
        if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                'SLOW REQUEST: %s %s took %.1fms',
                request.method,
                request.path,
                duration_ms,
            )

        return response
