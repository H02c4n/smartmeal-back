import uuid

from django.db import models

from .unit import UnitOfMeasure


class Ingredient(models.Model):
    """Malzeme. Reçetelerde kullanılır. Örn: un, domates, mercimek."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    base_unit = models.ForeignKey(
        UnitOfMeasure,
        on_delete=models.PROTECT,
        related_name="ingredients",
        help_text="Bu malzemenin stoklanacağı temel birim.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "catalog_ingredient"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.sku} — {self.name}"