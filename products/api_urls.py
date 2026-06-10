from django.urls import path
from .api_views import ShoeListAPIView, ShoeDetailAPIView

urlpatterns = [
    path('', ShoeListAPIView.as_view(), name='api-shoe-list'),
    path('<slug:slug>/', ShoeDetailAPIView.as_view(), name='api-shoe-detail'),
]
