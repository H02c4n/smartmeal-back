import uuid

from django.db import models


class Allergen(models.Model):
    """Alerjen sözlüğü. Örn: gluten, milk, egg, peanut."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "catalog_allergen"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name