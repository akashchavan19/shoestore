from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import RegisterView, CustomLoginView, ProfileView, ChangePasswordView

urlpatterns = [
    path('register/',        RegisterView.as_view(),       name='register'),
    path('login/',           CustomLoginView.as_view(),     name='login'),
    path('logout/',          LogoutView.as_view(next_page='home'), name='logout'),
    path('profile/',         ProfileView.as_view(),         name='profile'),
    path('change-password/', ChangePasswordView.as_view(),  name='change-password'),
]
