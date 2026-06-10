"""
accounts/services.py

All business logic for user accounts lives here.
Views and API views are thin — they validate input then call these services.

Principles followed:
- Every public method is a single responsibility
- DB writes use atomic transactions
- Errors raised as specific exceptions — callers decide how to respond
- All important actions are logged
- No Django request/response objects in here — pure business logic only
"""

import logging
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

logger = logging.getLogger('onistuka')


class AuthenticationError(Exception):
    """Raised when login credentials are invalid."""
    pass


class RegistrationError(Exception):
    """Raised when registration fails for a known reason."""
    pass


class UserService:
    """
    Handles user registration, profile updates, and account management.
    All methods are static — no instance state needed.
    """

    @staticmethod
    @transaction.atomic
    def register_user(
        username: str,
        email: str,
        password: str,
        first_name: str = '',
        last_name: str = '',
    ) -> User:
        """
        Creates a new user account.

        - Checks for duplicate username and email before creating
        - Wraps in atomic transaction — if profile creation fails, user is rolled back
        - Returns the created User object
        - Raises RegistrationError for known validation failures
        - Raises IntegrityError only for genuine race conditions (handled upstream)

        Args:
            username:   Unique username
            email:      Unique email address (stored lowercase)
            password:   Plain text password (Django hashes it)
            first_name: Optional
            last_name:  Optional

        Returns:
            User instance (profile auto-created via signal)

        Raises:
            RegistrationError: if username or email already exists
        """
        # Normalise email
        email = email.strip().lower()
        username = username.strip()

        # Check uniqueness before hitting the DB constraint
        # This gives us a clean error message instead of an IntegrityError
        if User.objects.filter(username__iexact=username).exists():
            raise RegistrationError('This username is already taken.')

        if User.objects.filter(email__iexact=email).exists():
            raise RegistrationError('An account with this email already exists.')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )

        logger.info(
            'New user registered: username=%s email=%s id=%s',
            user.username, user.email, user.id
        )
        return user

    @staticmethod
    def authenticate_user(username: str, password: str) -> User:
        """
        Authenticates a user by username or email + password.

        Supports login with either username or email — better UX.

        Returns:
            Authenticated User instance

        Raises:
            AuthenticationError: if credentials are invalid or account is inactive
        """
        username = username.strip()

        # Allow login by email as well
        if '@' in username:
            try:
                user_obj = User.objects.get(email__iexact=username)
                username = user_obj.username
            except User.DoesNotExist:
                # Don't reveal whether the email exists — fall through to fail
                raise AuthenticationError('Invalid credentials. Please try again.')

        user = authenticate(username=username, password=password)

        if user is None:
            logger.warning('Failed login attempt for username: %s', username)
            raise AuthenticationError('Invalid credentials. Please try again.')

        if not user.is_active:
            logger.warning('Login attempt on inactive account: %s', username)
            raise AuthenticationError('This account has been deactivated.')

        logger.info('User logged in: %s (id=%s)', user.username, user.id)
        return user

    @staticmethod
    @transaction.atomic
    def update_profile(user: User, data: dict) -> User:
        """
        Updates user and profile fields safely.

        Handles both User fields (first_name, last_name, email) and
        UserProfile fields (phone, avatar) in a single atomic transaction.

        Args:
            user: The User instance to update
            data: Dict of fields to update — only known fields are processed,
                  unknown keys are silently ignored (safe against mass assignment)

        Returns:
            Updated User instance

        Raises:
            RegistrationError: if new email is already taken by another account
            ValidationError: if phone number format is invalid
        """
        # Fields allowed to be updated — explicit whitelist (never **data)
        USER_FIELDS    = {'first_name', 'last_name', 'email'}
        PROFILE_FIELDS = {'phone', 'avatar'}

        user_dirty    = False
        profile_dirty = False

        # Update User fields
        for field in USER_FIELDS & data.keys():
            value = data[field]

            if field == 'email':
                value = value.strip().lower()
                # Check uniqueness excluding current user
                if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
                    raise RegistrationError('This email is already in use by another account.')

            setattr(user, field, value)
            user_dirty = True

        if user_dirty:
            user.save()

        # Update Profile fields
        profile = user.profile
        for field in PROFILE_FIELDS & data.keys():
            setattr(profile, field, data[field])
            profile_dirty = True

        if profile_dirty:
            profile.full_clean()   # runs field validators (e.g. phone regex)
            profile.save()

        logger.info('Profile updated for user: %s (id=%s)', user.username, user.id)
        return user
