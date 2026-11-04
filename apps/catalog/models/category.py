import uuid

from django.db import models


class ProductCategory(models.Model):
    """Ürün kategorisi. Örn: çorba, salata, ana yemek, tatlı."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "catalog_product_category"
        ordering = ["name"]
        verbose_name_plural = "Product categories"

    def __str__(self) -> str:
        return self.name