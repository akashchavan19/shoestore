"""
accounts/api_views.py

REST API views for authentication and user profile management.

Principles:
- Views are thin — validate input, call service, return response
- All business logic lives in services.py
- Consistent response shape: { success, data } or { success, error }
- Proper HTTP status codes on every response
- All endpoints explicitly declare permission_classes
"""

import logging
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .serializers import (
    UserRegistrationSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
    CustomTokenObtainPairSerializer,
)
from .services import UserService, AuthenticationError, RegistrationError

logger = logging.getLogger('onistuka')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterAPIView(APIView):
    """
    POST /api/v1/auth/register/

    Creates a new user and returns JWT tokens immediately —
    user is logged in right after registration, no extra step.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {'success': False, 'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        try:
            user = UserService.register_user(
                username   = data['username'],
                email      = data['email'],
                password   = data['password'],
                first_name = data.get('first_name', ''),
                last_name  = data.get('last_name', ''),
            )
        except RegistrationError as e:
            return Response(
                {'success': False, 'error': {'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        # Issue tokens immediately after registration
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'success': True,
                'message': 'Account created successfully.',
                'tokens': {
                    'access':  str(refresh.access_token),
                    'refresh': str(refresh),
                },
                'user': UserDetailSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Login / Token
# ---------------------------------------------------------------------------

class LoginAPIView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/

    Returns access + refresh tokens.
    CustomTokenObtainPairSerializer embeds user info in token payload.
    """
    permission_classes  = [AllowAny]
    serializer_class    = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            response.data = {
                'success': True,
                'tokens':  response.data,
            }
        return response


class TokenRefreshAPIView(TokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/

    Exchange a valid refresh token for a new access token.
    Old refresh token is blacklisted (ROTATE_REFRESH_TOKENS=True in settings).
    """
    pass


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutAPIView(APIView):
    """
    POST /api/v1/auth/logout/

    Blacklists the provided refresh token so it can't produce
    new access tokens. Client must also discard the access token locally.

    Body: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'success': False, 'error': {'message': 'Refresh token is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            # Token already blacklisted or invalid — still return success
            # Client treats this as a successful logout regardless
            pass

        logger.info('User logged out: %s (id=%s)', request.user.username, request.user.id)

        return Response(
            {'success': True, 'message': 'Logged out successfully.'},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class ProfileAPIView(APIView):
    """
    GET   /api/v1/auth/profile/  → full profile (User + UserProfile)
    PATCH /api/v1/auth/profile/  → update first_name, last_name, email, phone, avatar
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})

    def patch(self, request):
        serializer = UserUpdateSerializer(
            data    = request.data,
            context = {'request': request},
            partial = True,
        )

        if not serializer.is_valid():
            return Response(
                {'success': False, 'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = UserService.update_profile(
                user = request.user,
                data = serializer.validated_data,
            )
        except RegistrationError as e:
            return Response(
                {'success': False, 'error': {'message': str(e)}},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'success': True,
            'message': 'Profile updated successfully.',
            'data':    UserDetailSerializer(user).data,
        })
