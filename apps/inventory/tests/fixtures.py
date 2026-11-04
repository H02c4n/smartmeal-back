"""Inventory test yardımcıları."""
import uuid

from django.utils import timezone

from apps.catalog.models import Ingredient, UnitOfMeasure
from apps.inventory.models import InventoryLot, QualityStatus
from apps.purchasing.models import Supplier


def make_unit(code="g", name="gram"):
    return UnitOfMeasure.objects.get_or_create(code=code, defaults={"name": name})[0]


def make_ingredient(sku="ING-UN", name="Un", unit=None):
    unit = unit or make_unit()
    return Ingredient.objects.get_or_create(
        sku=sku, defaults={"name": name, "base_unit": unit}
    )[0]


def make_supplier(name="Default Supplier"):
    return Supplier.objects.get_or_create(name=name)[0]


def make_lot(
    ingredient=None,
    supplier=None,
    quality=QualityStatus.RELEASED,
    code=None,
):
    ingredient = ingredient or make_ingredient()
    supplier = supplier or make_supplier()
    code = code or f"LOT-{uuid.uuid4().hex[:8]}"
    return InventoryLot.objects.create(
        ingredient=ingredient,
        supplier=supplier,
        supplier_lot_code=code,
        internal_lot_code=code,
        received_at=timezone.now(),
        quality_status=quality,
    )