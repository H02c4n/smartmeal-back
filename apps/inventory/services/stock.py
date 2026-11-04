"""
Stok servisleri. `record_movement` dışında stok yazma yolu YOKTUR.
Dışarıdan StockMovement.objects.create() çağırmayın.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from apps.inventory.models import (
    InventoryLot,
    MovementType,
    QualityStatus,
    StockMovement,
)


def get_balance(lot: InventoryLot) -> Decimal:
    """Hareket defterinden hesaplanan fiziksel bakiye."""
    total = lot.movements.aggregate(total=Sum("quantity_delta"))["total"]
    return total or Decimal("0")


def get_available_balance(lot: InventoryLot) -> Decimal:
    """
    Fiziksel bakiye eksi aktif rezervasyonlar. Kalite kapısından
    geçmemişse 0.
    """
    if lot.quality_status != QualityStatus.RELEASED:
        return Decimal("0")

    balance = get_balance(lot)
    from apps.inventory.models import ReservationStatus  # local import

    reserved = (
        lot.reservations.filter(status=ReservationStatus.ACTIVE).aggregate(
            total=Sum("quantity")
        )["total"]
        or Decimal("0")
    )
    return max(balance - reserved, Decimal("0"))


# İşaret kuralları: miktar POZİTİF girilir, delta otomatik üretilir
_SIGN_RULES = {
    MovementType.RECEIPT: Decimal("1"),
    MovementType.CONSUMPTION: Decimal("-1"),
    MovementType.WASTE: Decimal("-1"),
    MovementType.RETURN: Decimal("1"),
    # ADJUSTMENT ve REVERSAL: quantity zaten signed
}


@transaction.atomic
def record_movement(
    *,
    lot_id,
    movement_type: str,
    quantity: Decimal,
    reason: str = "",
    actor=None,
    reference_type: str = "",
    reference_id=None,
) -> StockMovement:
    """
    Lot üzerinde hareket kaydeder. Lot satırı kilitlenir → eşzamanlı
    hareketler serialize olur; negatif bakiye oluşmaz.
    """
    if quantity is None:
        raise ValueError("quantity zorunlu.")
    quantity = Decimal(quantity)

    # 1) Lot'u kilitle (eşzamanlı hareketleri sıraya sokar)
    lot = InventoryLot.objects.select_for_update().get(pk=lot_id)

    # 2) Delta ve işaret doğrulaması
    if movement_type in _SIGN_RULES:
        if quantity < 0:
            raise ValueError(
                f"{movement_type} için pozitif miktar girin. "
                f"İşaret otomatik uygulanır."
            )
        delta = _SIGN_RULES[movement_type] * quantity
    elif movement_type in (MovementType.ADJUSTMENT, MovementType.REVERSAL):
        delta = quantity  # zaten signed
    else:
        raise ValueError(f"Bilinmeyen movement_type: {movement_type}")

    # 3) Negatif bakiye koruması
    if movement_type in (MovementType.CONSUMPTION, MovementType.WASTE):
        current = get_balance(lot)
        if current + delta < 0:
            raise ValueError(
                f"Yetersiz bakiye. Mevcut: {current}, istenen: {abs(delta)}."
            )

    # 4) Quality gate
    if movement_type == MovementType.CONSUMPTION and lot.quality_status != QualityStatus.RELEASED:
        raise ValueError(
            f"Lot durumu {lot.quality_status}; tüketim yapılamaz."
        )

    # 5) Kaydet
    return StockMovement.objects.create(
        lot=lot,
        movement_type=movement_type,
        quantity_delta=delta,
        reason=reason,
        actor=actor,
        reference_type=reference_type,
        reference_id=reference_id,
    )