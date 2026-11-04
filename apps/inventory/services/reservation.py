"""
Rezervasyon yaşam döngüsü servisleri. Reserve/release/consume/expire —
dışarıdan StockReservation.objects.create() çağırmayın.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import (
    MovementType,
    ReservationStatus,
    StockReservation,
)
from apps.inventory.services.stock import (
    get_available_balance,
    record_movement,
)


def _get_active_locked(reservation_id) -> StockReservation:
    """Rezervasyonu kilitle ve ACTIVE olduğunu doğrula."""
    r = StockReservation.objects.select_for_update().get(pk=reservation_id)
    if r.status != ReservationStatus.ACTIVE:
        raise ValueError(
            f"Yalnızca ACTIVE rezervasyon üzerinde işlem yapılabilir. "
            f"Mevcut: {r.status}."
        )
    return r


@transaction.atomic
def reserve(
    *,
    lot_id,
    quantity: Decimal,
    order_id=None,
    ttl_hours: int = 24,
    actor=None,
) -> StockReservation:
    """
    Lot'tan `quantity` kadar rezervasyon yaratır. Lot satırı kilitlenir;
    eşzamanlı rezervasyonlar serialize olur ve available aşılmaz.
    """
    if quantity is None or Decimal(quantity) <= 0:
        raise ValueError("Rezervasyon miktarı pozitif olmalı.")
    quantity = Decimal(quantity)

    from apps.inventory.models import InventoryLot

    lot = InventoryLot.objects.select_for_update().get(pk=lot_id)

    available = get_available_balance(lot)
    if quantity > available:
        raise ValueError(
            f"Yetersiz kullanılabilir bakiye. "
            f"İstenen: {quantity}, mevcut: {available}."
        )

    return StockReservation.objects.create(
        lot=lot,
        quantity=quantity,
        order_id=order_id,
        expires_at=timezone.now() + timezone.timedelta(hours=ttl_hours),
        actor=actor,
    )


@transaction.atomic
def release(*, reservation_id, actor=None) -> StockReservation:
    """ACTIVE → RELEASED. Hareket yazılmaz; available artar."""
    r = _get_active_locked(reservation_id)
    r.status = ReservationStatus.RELEASED
    r.closed_at = timezone.now()
    r.save(update_fields=["status", "closed_at"])
    return r


@transaction.atomic
def consume(*, reservation_id, actor=None) -> StockReservation:
    """
    ACTIVE → CONSUMED. Fiziksel CONSUMPTION hareketini atomik olarak
    yazar. Rezervasyon ve hareketin tutarlı kalması için tek transaction.
    """
    r = _get_active_locked(reservation_id)

    record_movement(
        lot_id=r.lot_id,
        movement_type=MovementType.CONSUMPTION,
        quantity=r.quantity,
        reason=f"Consumed reservation {r.id}",
        reference_type="StockReservation",
        reference_id=r.id,
        actor=actor,
    )

    r.status = ReservationStatus.CONSUMED
    r.closed_at = timezone.now()
    r.save(update_fields=["status", "closed_at"])
    return r


@transaction.atomic
def expire_stale() -> int:
    """
    Süresi geçmiş ACTIVE rezervasyonları EXPIRED'a çeker.
    Döndürülen: güncellenen satır sayısı.
    """
    now = timezone.now()
    return StockReservation.objects.filter(
        status=ReservationStatus.ACTIVE,
        expires_at__lt=now,
    ).update(status=ReservationStatus.EXPIRED, closed_at=now)