"""
onistuka/throttles.py

Custom DRF throttle classes for Phase 5.

AuthRateThrottle:
- Applied to login and register endpoints only
- Much stricter than general API throttle (10/minute vs 60/minute)
- Protects against brute force attacks on credentials
"""

from rest_framework.throttling import AnonRateThrottle


class AuthRateThrottle(AnonRateThrottle):
    """
    Strict throttle for authentication endpoints.
    10 attempts per minute per IP — stops brute force attacks.
    Rate defined in settings: REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['auth']
    """
    scope = 'auth'
