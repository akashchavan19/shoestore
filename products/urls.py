from django.urls import path
from .views import (
    HomeView,
    ShoeListView,
    ShoeDetailView,
    MenShoeListView,
    WomenShoeListView,
    ShoeSearchView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('shoes/', ShoeListView.as_view(), name='shoe-list'),
    path('shoes/<slug:slug>/', ShoeDetailView.as_view(), name='shoe-detail'),  # slug, not pk
    path('men/', MenShoeListView.as_view(), name='men-shoes'),
    path('women/', WomenShoeListView.as_view(), name='women-shoes'),
    path('search/', ShoeSearchView.as_view(), name='shoe-search'),
]
