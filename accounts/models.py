"""
accounts/models.py

UserProfile extends Django's built-in User with additional fields.
Uses a post_save signal to auto-create/save the profile whenever
a User is created or updated.

Design decisions:
- OneToOneField — one profile per user, enforced at DB level
- phone as CharField — phone numbers are not integers (+91, leading zeros)
- avatar path organised by user id — avoids filename collisions
- is_email_verified — used by email verification flow
- is_first_time_user — used by coupon system (first-user discount)
- All fields nullable/blank so profile creation never fails at signal time
"""

import logging
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger('onistuka')


def avatar_upload_path(instance, filename):
    """Store avatars as media/avatars/user_<id>/avatar.<ext>"""
    ext = filename.rsplit('.', 1)[-1].lower()
    return f'avatars/user_{instance.user.id}/avatar.{ext}'


class UserProfile(models.Model):
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message='Enter a valid phone number (e.g. +919876543210 or 9876543210).'
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[phone_validator],
    )
    avatar = models.ImageField(
        upload_to=avatar_upload_path,
        null=True,
        blank=True,
    )
    is_email_verified = models.BooleanField(default=False)
    is_first_time_user = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'Profile — {self.user.username}'

    def get_display_name(self):
        return self.user.first_name or self.user.username

    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        return None


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=User)
def handle_user_profile(sender, instance, created, **kwargs):
    """
    Auto-create profile on new user.
    Auto-save profile on existing user update.
    Runs inside same DB transaction as the User save.
    """
    if created:
        UserProfile.objects.create(user=instance)
        logger.info('UserProfile created for user: %s (id=%s)', instance.username, instance.id)
    else:
        # get_or_create handles edge cases where profile was missing
        profile, was_created = UserProfile.objects.get_or_create(user=instance)
        if was_created:
            logger.warning('UserProfile was missing for existing user %s — created now.', instance.username)
