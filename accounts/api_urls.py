from django.urls import path
from .api_views import (
    RegisterAPIView,
    LoginAPIView,
    TokenRefreshAPIView,
    LogoutAPIView,
    ProfileAPIView,
)

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='api-register'),
    path('login/', LoginAPIView.as_view(), name='api-login'),
    path('token/refresh/', TokenRefreshAPIView.as_view(), name='api-token-refresh'),
    path('logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('profile/', ProfileAPIView.as_view(), name='api-profile'),
]
