from rest_framework import generics, filters
from rest_framework.permissions import AllowAny
from .models import Shoe
from .serializers import ShoeListSerializer, ShoeDetailSerializer


class ShoeListAPIView(generics.ListAPIView):
    """
    GET /api/v1/products/
    Returns paginated list of active shoes.
    Supports:  ?search=nike   ?category=Men   ?ordering=price
    """
    serializer_class = ShoeListSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'brand', 'description']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Shoe.objects.filter(is_active=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class ShoeDetailAPIView(generics.RetrieveAPIView):
    """
    GET /api/v1/products/<slug>/
    Returns full detail for one shoe.
    """
    serializer_class = ShoeDetailSerializer
    permission_classes = [AllowAny]
    queryset = Shoe.objects.filter(is_active=True)
    lookup_field = 'slug'
