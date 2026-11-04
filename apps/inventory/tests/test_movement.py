"""StockMovement model testleri (append-only)."""
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.inventory.models import MovementType, StockMovement

from apps.inventory.tests.fixtures import make_lot


@pytest.mark.django_db
class TestStockMovementAppendOnly:
    def test_create_receipt(self):
        lot = make_lot()
        m = StockMovement.objects.create(
            lot=lot,
            movement_type=MovementType.RECEIPT,
            quantity_delta=Decimal("100"),
        )
        assert m.quantity_delta == Decimal("100")
        assert m.lot == lot

    def test_update_raises(self):
        lot = make_lot()
        m = StockMovement.objects.create(
            lot=lot,
            movement_type=MovementType.RECEIPT,
            quantity_delta=Decimal("100"),
        )
        m.quantity_delta = Decimal("50")
        with pytest.raises(ValidationError):
            m.save()

    def test_delete_raises(self):
        lot = make_lot()
        m = StockMovement.objects.create(
            lot=lot,
            movement_type=MovementType.RECEIPT,
            quantity_delta=Decimal("100"),
        )
        with pytest.raises(ValidationError):
            m.delete()
        assert StockMovement.objects.filter(pk=m.pk).exists()

    def test_clean_rejects_receipt_with_negative_delta(self):
        lot = make_lot()
        m = StockMovement(
            lot=lot,
            movement_type=MovementType.RECEIPT,
            quantity_delta=Decimal("-10"),
        )
        with pytest.raises(ValidationError):
            m.full_clean()