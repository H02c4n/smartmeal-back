import uuid

from django.db import models


class Supplier(models.Model):
    """Tedarikçi. Mal kabul / lot kaynağı."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    contact_person = models.CharField(max_length=128, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchasing_supplier"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name