"""
Sipariş durum geçiş servisleri. PLACED → CONFIRMED (rezervasyonlu) ve
CONFIRMED/PLACED → CANCELLED (rezervasyonları serbest bırakır).

Bu modül `order.create_order`'dan ayrı: bir kaydın yaratılması ile
durum değiştirmesi farklı sorumluluklar.
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.inventory.models import (
    InventoryLot,
    QualityStatus,
    ReservationStatus,
    StockReservation,
)
from apps.inventory.services.reservation import release, reserve
from apps.inventory.services.stock import get_available_balance
from apps.orders.models import Order, OrderStatus


# ---------------------------------------------------------------------------
# İç yardımcılar
# ---------------------------------------------------------------------------
def _fmt_d(value) -> str:
    """Decimal('5.000') → '5', Decimal('5.500') → '5.5' — gereksiz sıfırları sil."""
    if value is None:
        return "?"
    return format(value.normalize(), "f")

def _aggregate_ingredient_needs(order: Order) -> dict:
    """
    Siparişteki tüm satırlardan toplam malzeme ihtiyacını hesaplar.
    Döndürülen: {ingredient_id: Decimal(toplam_miktar)}
    """
    needs: dict = defaultdict(lambda: Decimal("0"))
    for line in order.lines.select_related("recipe_version_snapshot").prefetch_related(
        "recipe_version_snapshot__lines"
    ):
        recipe = line.recipe_version_snapshot
        if recipe is None:
            raise ValueError(
                f"{line.product_name_snapshot} için onaylı reçete yok. "
                f"Sipariş onaylanamaz."
            )
        if recipe.yield_quantity is None or recipe.yield_quantity <= 0:
            raise ValueError(
                f"Reçete {recipe.id} için geçersiz yield_quantity."
            )

        multiplier = Decimal(line.quantity) / recipe.yield_quantity
        for rl in recipe.lines.all():
            needs[rl.ingredient_id] += rl.quantity * multiplier
    return dict(needs)


def _allocate_fefo(needs: dict) -> list[tuple]:
    """
    Her malzeme için FEFO (earliest expiry first) sırasıyla lot seçer.
    Döndürülen: [(lot, quantity), ...]. Toplam her malzeme için ihtiyacı
    karşılamıyorsa ValueError fırlatır.
    """
    from apps.catalog.models import Ingredient

    allocations: list[tuple] = []
    for ingredient_id, needed in needs.items():
        remaining = needed
        available_total = Decimal("0")

        lots = InventoryLot.objects.filter(
            ingredient_id=ingredient_id,
            quality_status=QualityStatus.RELEASED,
        ).order_by(F("expiry_date").asc(nulls_last=True), "received_at")

        for lot in lots:
            if remaining <= 0:
                break
            avail = get_available_balance(lot)
            available_total += avail
            if avail <= 0:
                continue
            take = min(remaining, avail)
            allocations.append((lot, take))
            remaining -= take

        if remaining > 0:
            ingredient = (
                Ingredient.objects.select_related("base_unit")
                .filter(pk=ingredient_id)
                .first()
            )
            if ingredient:
                unit = (
                    ingredient.base_unit.code if ingredient.base_unit else "adet"
                )
                label = f"{ingredient.name} ({ingredient.sku})"
            else:
                unit = "adet"
                label = str(ingredient_id)

            raise ValueError(
                f"Yetersiz stok: {label} — "
                f"İstenen: {_fmt_d(needed)} {unit}, "
                f"mevcut: {_fmt_d(available_total)} {unit}, "
                f"eksik: {_fmt_d(remaining)} {unit}."
            )
    return allocations


# ---------------------------------------------------------------------------
# Public servisler
# ---------------------------------------------------------------------------
@transaction.atomic
def confirm_order(*, order_id, actor=None) -> Order:
    """
    PLACED → CONFIRMED. Her malzeme için rezervasyon yapar. Herhangi bir
    adım başarısız olursa transaction bütünüyle geri alınır → sipariş
    PLACED'da kalır, hiç rezervasyon oluşmaz.
    """
    order = Order.objects.select_for_update().get(pk=order_id)

    if order.status != OrderStatus.PLACED:
        raise ValueError(
            f"Yalnızca PLACED sipariş CONFIRMED'a alınabilir. "
            f"Mevcut: {order.status}."
        )

    # 1) İhtiyaçları hesapla (reçetesiz satır varsa burada patlar)
    needs = _aggregate_ingredient_needs(order)

    # 2) FEFO tahsis (yetersizse burada patlar)
    allocations = _allocate_fefo(needs)

    # 3) Rezervasyonları oluştur. reserve() kendi içinde lot'u kilitler
    #    ve available kontrolü yapar. Yarış olursa burada patlar → rollback.
    for lot, qty in allocations:
        reserve(
            lot_id=lot.id,
            quantity=qty,
            order_id=order.id,
            actor=actor,
        )

    # 4) Durumu güncelle
    order.status = OrderStatus.CONFIRMED
    order.confirmed_at = timezone.now()
    order.save(update_fields=["status", "confirmed_at", "updated_at"])
    return order


@transaction.atomic
def cancel_order(*, order_id, reason: str = "", actor=None) -> Order:
    """
    PLACED veya CONFIRMED → CANCELLED. CONFIRMED ise tüm aktif
    rezervasyonlar serbest bırakılır.
    """
    order = Order.objects.select_for_update().get(pk=order_id)

    if order.status not in (OrderStatus.PLACED, OrderStatus.CONFIRMED):
        raise ValueError(
            f"İptal edilemez. Mevcut durum: {order.status}."
        )

    # Aktif rezervasyonları serbest bırak
    active = list(
        StockReservation.objects.filter(
            order_id=order.id, status=ReservationStatus.ACTIVE
        )
    )
    for r in active:
        release(reservation_id=r.id, actor=actor)

    order.status = OrderStatus.CANCELLED
    order.cancelled_at = timezone.now()
    order.cancellation_reason = reason
    order.save(
        update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"]
    )
    return order