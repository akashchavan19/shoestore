from django.db import models
from django.utils.text import slugify


class Shoe(models.Model):
    CATEGORY_CHOICES = [
        ('Men', 'Men'),
        ('Women', 'Women'),
        ('Unisex', 'Unisex'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    brand = models.CharField(max_length=100)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # Comma-separated sizes stored as text; parsed via get_size_list()
    available_sizes = models.CharField(max_length=100)
    image = models.ImageField(upload_to='shoes/')
    description = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)  # Soft-delete / hide product
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['brand']),
        ]

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not set
        if not self.slug:
            base_slug = slugify(f"{self.brand}-{self.name}")
            slug = base_slug
            counter = 1
            while Shoe.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_size_list(self):
        """Return list of available sizes, stripping whitespace."""
        return [s.strip() for s in self.available_sizes.split(',') if s.strip()]

    def __str__(self):
        return f"{self.brand} — {self.name}"


# ---------------------------------------------------------------------------
# Cache invalidation signal
# ---------------------------------------------------------------------------
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache


@receiver([post_save, post_delete], sender=Shoe)
def invalidate_shoe_cache(sender, instance, **kwargs):
    """
    Clears product list caches whenever a shoe is saved or deleted.
    This ensures admins see changes immediately without waiting for TTL.
    Uses cache.delete_pattern if available (Redis), otherwise clears all.
    """
    try:
        # Redis supports pattern deletion
        cache.delete_pattern('*shoe_list*')
        cache.delete_pattern('*shoe_detail*')
        cache.delete(f'shoe_detail_{instance.slug}')
    except AttributeError:
        # LocMemCache doesn't support patterns — just clear all
        cache.clear()
