"""
accounts/views.py

Template-rendered auth views (login / register / logout).
On login, merges the anonymous session cart into the user's account.
"""

import logging
from django.contrib.auth import login, logout, update_session_auth_hash
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.shortcuts import redirect
from django.contrib import messages

from .forms import CustomUserRegistrationForm
from .services import UserService, RegistrationError
from cart.services import CartService

logger = logging.getLogger('onistuka')


class RegisterView(CreateView):
    form_class    = CustomUserRegistrationForm
    template_name = 'accounts/register.html'
    success_url   = reverse_lazy('home')

    def form_valid(self, form):
        # Get session key BEFORE login (login may rotate the session)
        session_key = self.request.session.session_key

        user = form.save()
        login(self.request, user)

        # Merge any anonymous cart items into the new user's cart
        if session_key:
            CartService.merge_session_cart_into_user(user=user, session_key=session_key)

        messages.success(self.request, f'Welcome to Onistuka, {user.first_name or user.username}!')
        return redirect(self.success_url)


class CustomLoginView(LoginView):
    """
    Extends Django's LoginView to merge the session cart on login.
    """
    template_name             = 'accounts/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.request.GET.get('next') or reverse_lazy('home')

    def form_valid(self, form):
        # Capture session key before login() rotates the session
        session_key = self.request.session.session_key

        user = form.get_user()
        login(self.request, user)

        # Merge anonymous cart → user cart
        if session_key:
            CartService.merge_session_cart_into_user(user=user, session_key=session_key)

        logger.info('User logged in via template view: %s', user.username)
        return redirect(self.get_success_url())


class ProfileView(LoginRequiredMixin, View):
    """
    GET  /accounts/profile/ — show profile with editable fields
    POST /accounts/profile/ — update first_name, last_name, email, phone
    """
    template_name = 'accounts/profile.html'

    def get(self, request):
        from django.shortcuts import render
        return render(request, self.template_name, {'user': request.user})

    def post(self, request):
        data = {
            'first_name': request.POST.get('first_name', '').strip(),
            'last_name':  request.POST.get('last_name', '').strip(),
            'email':      request.POST.get('email', '').strip(),
            'phone':      request.POST.get('phone', '').strip(),
        }

        try:
            UserService.update_profile(user=request.user, data=data)
            messages.success(request, 'Profile updated successfully.')
        except RegistrationError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, 'Something went wrong. Please try again.')

        return redirect('profile')


class ChangePasswordView(LoginRequiredMixin, View):
    """
    POST /accounts/change-password/ — change password
    """
    def post(self, request):
        current  = request.POST.get('current_password', '')
        new      = request.POST.get('new_password', '')
        confirm  = request.POST.get('confirm_password', '')

        if not request.user.check_password(current):
            messages.error(request, 'Current password is incorrect.')
            return redirect('profile')

        if len(new) < 8:
            messages.error(request, 'New password must be at least 8 characters.')
            return redirect('profile')

        if new != confirm:
            messages.error(request, 'New passwords do not match.')
            return redirect('profile')

        request.user.set_password(new)
        request.user.save()
        # Keep the user logged in after password change
        update_session_auth_hash(request, request.user)
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')
