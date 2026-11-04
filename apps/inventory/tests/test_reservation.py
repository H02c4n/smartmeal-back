"""Rezervasyon servis testleri."""
import threading
import uuid
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory.models import (
    MovementType,
    QualityStatus,
    ReservationStatus,
)
from apps.inventory.services.reservation import (
    consume,
    expire_stale,
    release,
    reserve,
)
from apps.inventory.services.stock import (
    get_available_balance,
    get_balance,
    record_movement,
)

from apps.inventory.tests.fixtures import make_lot


def _fund(lot, qty=100):
    return record_movement(
        lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal(str(qty))
    )


@pytest.mark.django_db
class TestReserve:
    def test_reserve_reduces_available(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        assert r.status == ReservationStatus.ACTIVE
        assert get_balance(lot) == Decimal("100")
        assert get_available_balance(lot) == Decimal("40")

    def test_reserve_more_than_available_fails(self):
        lot = make_lot()
        _fund(lot, 100)
        with pytest.raises(ValueError, match="Yetersiz kullanılabilir"):
            reserve(lot_id=lot.id, quantity=Decimal("150"))

    def test_reserve_on_pending_lot_fails(self):
        lot = make_lot(quality=QualityStatus.PENDING)
        _fund(lot, 100)
        with pytest.raises(ValueError, match="Yetersiz kullanılabilir"):
            reserve(lot_id=lot.id, quantity=Decimal("10"))

    def test_multiple_reservations_sum(self):
        lot = make_lot()
        _fund(lot, 100)
        reserve(lot_id=lot.id, quantity=Decimal("30"))
        reserve(lot_id=lot.id, quantity=Decimal("20"))
        assert get_available_balance(lot) == Decimal("50")

    def test_reserve_zero_or_negative_fails(self):
        lot = make_lot()
        _fund(lot, 100)
        with pytest.raises(ValueError):
            reserve(lot_id=lot.id, quantity=Decimal("0"))


@pytest.mark.django_db
class TestRelease:
    def test_release_restores_available(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        assert get_available_balance(lot) == Decimal("40")
        release(reservation_id=r.id)
        r.refresh_from_db()
        assert r.status == ReservationStatus.RELEASED
        assert r.closed_at is not None
        assert get_available_balance(lot) == Decimal("100")

    def test_release_twice_fails(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        release(reservation_id=r.id)
        with pytest.raises(ValueError, match="ACTIVE"):
            release(reservation_id=r.id)


@pytest.mark.django_db
class TestConsume:
    def test_consume_writes_movement_and_closes(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        consumed = consume(reservation_id=r.id)
        assert consumed.status == ReservationStatus.CONSUMED
        assert consumed.closed_at is not None
        assert get_balance(lot) == Decimal("40")
        assert get_available_balance(lot) == Decimal("40")
        # Hareket yazıldı mı
        m = lot.movements.get(movement_type=MovementType.CONSUMPTION)
        assert m.reference_type == "StockReservation"
        assert m.reference_id == r.id
        assert m.quantity_delta == Decimal("-60")

    def test_consume_non_active_fails(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        release(reservation_id=r.id)
        with pytest.raises(ValueError, match="ACTIVE"):
            consume(reservation_id=r.id)


@pytest.mark.django_db
class TestExpireStale:
    def test_expire_old_active(self):
        lot = make_lot()
        _fund(lot, 100)
        r = reserve(lot_id=lot.id, quantity=Decimal("60"))
        # expires_at'i geçmişe çek
        r.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        r.save(update_fields=["expires_at"])

        count = expire_stale()
        assert count == 1
        r.refresh_from_db()
        assert r.status == ReservationStatus.EXPIRED
        assert r.closed_at is not None
        assert get_available_balance(lot) == Decimal("100")

    def test_expire_ignores_future_active(self):
        lot = make_lot()
        _fund(lot, 100)
        reserve(lot_id=lot.id, quantity=Decimal("60"))  # expires_at = now+24h
        count = expire_stale()
        assert count == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_reservations_do_not_oversell():
    """
    Lot'ta 100 var. İki thread paralel 60 rezerve etmeye çalışır.
    select_for_update lot'u kilitler → biri başarılı (→40 available),
    diğeri 'yetersiz' hatası.
    """
    lot = make_lot()
    _fund(lot, 100)

    barrier = threading.Barrier(2)
    successes, errors = [], []

    def try_reserve():
        try:
            barrier.wait()
            reserve(lot_id=lot.id, quantity=Decimal("60"))
            successes.append(True)
        except ValueError as e:
            errors.append(str(e))
        finally:
            from django.db import connections
            connections.close_all()

    threads = [threading.Thread(target=try_reserve) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(successes) == 1
    assert len(errors) == 1
    assert "Yetersiz kullanılabilir" in errors[0]
    lot.refresh_from_db()
    assert get_available_balance(lot) == Decimal("40")