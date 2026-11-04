"""InventoryLot model testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.inventory.models import InventoryLot, QualityStatus

from apps.inventory.tests.fixtures import make_ingredient, make_lot, make_supplier


@pytest.mark.django_db
class TestInventoryLot:
    def test_create_default_pending(self):
        lot = make_lot(quality=QualityStatus.PENDING)
        assert lot.quality_status == QualityStatus.PENDING
        assert str(lot).startswith("LOT-")

    def test_internal_lot_code_unique(self):
        ing = make_ingredient()
        sup = make_supplier()
        make_lot(ingredient=ing, supplier=sup, code="L-X")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                InventoryLot.objects.create(
                    ingredient=ing,
                    supplier=sup,
                    supplier_lot_code="S-X",
                    internal_lot_code="L-X",
                    received_at="2026-01-01T00:00:00Z",
                )

    def test_supplier_lot_unique_per_ingredient(self):
        ing = make_ingredient()
        sup = make_supplier()
        make_lot(ingredient=ing, supplier=sup, code="L1")  # supplier_lot_code=L1
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                InventoryLot.objects.create(
                    ingredient=ing,
                    supplier=sup,
                    supplier_lot_code="L1",
                    internal_lot_code="L2",
                    received_at="2026-01-01T00:00:00Z",
                )