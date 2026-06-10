from rest_framework import serializers
from .models import Shoe


class ShoeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no heavy fields."""
    size_list = serializers.SerializerMethodField()

    class Meta:
        model = Shoe
        fields = ['id', 'slug', 'name', 'brand', 'category', 'price', 'image', 'size_list']

    def get_size_list(self, obj):
        return obj.get_size_list()


class ShoeDetailSerializer(serializers.ModelSerializer):
    """Full serializer for detail view."""
    size_list = serializers.SerializerMethodField()

    class Meta:
        model = Shoe
        fields = [
            'id', 'slug', 'name', 'brand', 'category',
            'price', 'image', 'description',
            'available_sizes', 'size_list',
            'is_active', 'created_at',
        ]

    def get_size_list(self, obj):
        return obj.get_size_list()
