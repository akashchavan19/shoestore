"""
accounts/serializers.py

DRF serializers for the accounts app.
Each serializer has one clear job — validates input and shapes output.

Principles:
- write_only on passwords — never returned in responses
- explicit field lists — no ModelSerializer with fields='__all__'
- validate_<field> methods for field-level validation
- validate() for cross-field validation (e.g. password match)
- Custom JWT serializer embeds user info in token payload
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT payload with basic user info.
    Frontend can decode the token and show username/email
    without a separate /me API call on every page load.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username']   = user.username
        token['email']      = user.email
        token['first_name'] = user.first_name
        token['last_name']  = user.last_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user snapshot to response body
        data['user'] = UserSummarySerializer(self.user).data
        return data


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class UserRegistrationSerializer(serializers.Serializer):
    """
    Validates new user registration input.
    Uses Serializer (not ModelSerializer) for full control over
    validation order and error messages.
    """
    first_name = serializers.CharField(max_length=30)
    last_name  = serializers.CharField(max_length=30)
    email      = serializers.EmailField()
    username   = serializers.CharField(max_length=150, min_length=3)
    password   = serializers.CharField(write_only=True, min_length=8)
    password2  = serializers.CharField(write_only=True, label='Confirm password')

    def validate_username(self, value):
        if not value.replace('_', '').replace('.', '').isalnum():
            raise serializers.ValidationError(
                'Username may only contain letters, numbers, underscores, and dots.'
            )
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value.strip()

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': 'Passwords do not match.'})
        return data


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

class UserSummarySerializer(serializers.ModelSerializer):
    """
    Lightweight read-only user snapshot.
    Embedded in JWT response and other places where
    we need basic user info without the full profile.
    """
    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Read/update the UserProfile extended fields.
    avatar returned as full URL via SerializerMethodField.
    """
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model  = UserProfile
        fields = ['phone', 'avatar', 'avatar_url', 'is_email_verified', 'is_first_time_user', 'updated_at']
        read_only_fields = ['is_email_verified', 'is_first_time_user', 'avatar_url', 'updated_at']
        extra_kwargs = {
            'avatar': {'write_only': True},  # clients upload via avatar, receive via avatar_url
        }

    def get_avatar_url(self, obj):
        return obj.get_avatar_url()


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Full profile read — combines User + UserProfile.
    Used for GET /api/v1/auth/profile/
    """
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'profile']
        read_only_fields = ['id', 'username', 'date_joined']


class UserUpdateSerializer(serializers.Serializer):
    """
    Validates profile update input.
    PATCH /api/v1/auth/profile/
    Only the fields listed here can be updated — explicit whitelist.
    """
    first_name = serializers.CharField(max_length=30, required=False)
    last_name  = serializers.CharField(max_length=30, required=False)
    email      = serializers.EmailField(required=False)
    phone      = serializers.CharField(max_length=15, required=False, allow_blank=True)
    avatar     = serializers.ImageField(required=False)

    def validate_email(self, value):
        value = value.strip().lower()
        request = self.context.get('request')
        if request and User.objects.filter(email__iexact=value).exclude(pk=request.user.pk).exists():
            raise serializers.ValidationError('This email is already in use by another account.')
        return value
