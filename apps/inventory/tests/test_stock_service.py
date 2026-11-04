"""record_movement ve bakiye hesaplama testleri."""
import threading
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory.models import MovementType, QualityStatus
from apps.inventory.services.stock import (
    get_available_balance,
    get_balance,
    record_movement,
)

from apps.inventory.tests.fixtures import make_lot


@pytest.mark.django_db
class TestRecordMovement:
    def test_receipt_increases_balance(self):
        lot = make_lot()
        record_movement(
            lot_id=lot.id,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("100"),
        )
        assert get_balance(lot) == Decimal("100")

    def test_consumption_decreases_balance(self):
        lot = make_lot()
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        record_movement(lot_id=lot.id, movement_type=MovementType.CONSUMPTION, quantity=Decimal("30"))
        assert get_balance(lot) == Decimal("70")

    def test_consumption_exceeding_balance_raises(self):
        lot = make_lot()
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("50"))
        with pytest.raises(ValueError, match="Yetersiz bakiye"):
            record_movement(
                lot_id=lot.id,
                movement_type=MovementType.CONSUMPTION,
                quantity=Decimal("60"),
            )

    def test_consumption_on_pending_lot_raises(self):
        lot = make_lot(quality=QualityStatus.PENDING)
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        with pytest.raises(ValueError, match="tüketim yapılamaz"):
            record_movement(
                lot_id=lot.id,
                movement_type=MovementType.CONSUMPTION,
                quantity=Decimal("10"),
            )

    def test_receipt_negative_quantity_raises(self):
        lot = make_lot()
        with pytest.raises(ValueError, match="pozitif miktar"):
            record_movement(
                lot_id=lot.id,
                movement_type=MovementType.RECEIPT,
                quantity=Decimal("-10"),
            )

    def test_adjustment_accepts_signed_quantity(self):
        lot = make_lot()
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        record_movement(
            lot_id=lot.id,
            movement_type=MovementType.ADJUSTMENT,
            quantity=Decimal("-5"),
            reason="sayım farkı",
        )
        assert get_balance(lot) == Decimal("95")

    def test_reversal_negates_original(self):
        lot = make_lot()
        m = record_movement(
            lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100")
        )
        record_movement(
            lot_id=lot.id,
            movement_type=MovementType.REVERSAL,
            quantity=-m.quantity_delta,
            reason="iptal",
            reference_type="StockMovement",
            reference_id=m.id,
        )
        assert get_balance(lot) == Decimal("0")

    def test_available_balance_zero_for_pending(self):
        lot = make_lot(quality=QualityStatus.PENDING)
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        assert get_balance(lot) == Decimal("100")
        assert get_available_balance(lot) == Decimal("0")

    def test_available_balance_equals_balance_for_released(self):
        lot = make_lot(quality=QualityStatus.RELEASED)
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        assert get_available_balance(lot) == Decimal("100")


@pytest.mark.django_db(transaction=True)
def test_concurrent_consumptions_do_not_oversell():
    """
    Aynı lot'a paralel iki CONSUMPTION(60). Bakiye 100.
    Biri başarılı (→40), diğeri 'yetersiz bakiye' hatası vermeli.
    select_for_update lot'u kilitler → serialize olur.
    """
    lot = make_lot()
    record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))

    barrier = threading.Barrier(2)
    successes = []
    errors = []

    def consume():
        try:
            barrier.wait()
            record_movement(
                lot_id=lot.id,
                movement_type=MovementType.CONSUMPTION,
                quantity=Decimal("60"),
            )
            successes.append(True)
        except ValueError as e:
            errors.append(str(e))
        finally:
            from django.db import connections
            connections.close_all()

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(successes) == 1
    assert len(errors) == 1
    assert "Yetersiz bakiye" in errors[0]
    lot.refresh_from_db()
    assert get_balance(lot) == Decimal("40")