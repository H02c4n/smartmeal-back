import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from apps.catalog.models import Ingredient, UnitOfMeasure

from .recipe_version import RecipeVersion


class RecipeLine(models.Model):
    """Bir reçete sürümündeki malzeme satırı."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe_version = models.ForeignKey(
        RecipeVersion, on_delete=models.CASCADE, related_name="lines"
    )
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT, related_name="recipe_lines"
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit = models.ForeignKey(
        UnitOfMeasure, on_delete=models.PROTECT, related_name="recipe_lines"
    )
    waste_factor = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("1.000"),
        help_text="1.05 = %5 fire payı. Fire hesabı ileride netleştirilecek.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recipes_recipe_line"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe_version", "ingredient"],
                name="uniq_version_ingredient",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recipe_version} — {self.ingredient.sku} ({self.quantity} {self.unit.code})"

    def save(self, *args, **kwargs):
        # Kilitli sürüme satır eklenemez / güncellenemez.
        if self._state.adding and self.recipe_version.is_locked:
            raise ValidationError(
                "Onaylanmış sürüme satır eklenemez. Yeni sürüm oluşturun."
            )
        if not self._state.adding:
            db_obj = RecipeLine.objects.select_related("recipe_version").filter(pk=self.pk).first()
            if db_obj and db_obj.recipe_version.is_locked:
                raise ValidationError(
                    "Onaylanmış sürümün satırı değiştirilemez."
                )
        super().save(*args, **kwargs)