"""
Üretim yürütme servisleri. Batch durum geçişleri ve stok tüketimi.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockReservation
from apps.inventory.services.reservation import consume
from apps.production.models import (
    BatchIngredient,
    ProductionBatch,
    ProductionBatchStatus,
    ProductionPlanStatus,
)


def _get_locked_batch(batch_id) -> ProductionBatch:
    return ProductionBatch.objects.select_for_update().get(pk=batch_id)


@transaction.atomic
def start_batch(*, batch_id, actor=None) -> ProductionBatch:
    """PLANNED → IN_PROGRESS. İlk batch başlarsa plan da IN_PROGRESS olur."""
    batch = _get_locked_batch(batch_id)

    if batch.status != ProductionBatchStatus.PLANNED:
        raise ValueError(
            f"Yalnızca PLANNED batch başlatılabilir. Mevcut: {batch.status}."
        )

    batch.status = ProductionBatchStatus.IN_PROGRESS
    batch.started_at = timezone.now()
    batch.save(update_fields=["status", "started_at", "updated_at"])

    # Plan DRAFT ise RELEASED'a (opsiyonel otomatik geçiş)
    plan = batch.plan
    if plan.status == ProductionPlanStatus.DRAFT:
        plan.status = ProductionPlanStatus.RELEASED
        plan.released_at = timezone.now()
        plan.save(update_fields=["status", "released_at", "updated_at"])

    # Plan RELEASED ise IN_PROGRESS'a
    if plan.status == ProductionPlanStatus.RELEASED:
        plan.status = ProductionPlanStatus.IN_PROGRESS
        plan.save(update_fields=["status", "updated_at"])

    return batch


@transaction.atomic
def complete_batch(
    *,
    batch_id,
    actual_quantity: int | None = None,
    waste_quantity: Decimal = Decimal("0"),
    actor=None,
) -> ProductionBatch:
    """
    IN_PROGRESS → COMPLETED.

    Siparişin **tüm** batch'leri tamamlandıysa aktif rezervasyonlar
    consume edilir ve BatchIngredient satırları yazılır.
    """
    batch = _get_locked_batch(batch_id)

    if batch.status != ProductionBatchStatus.IN_PROGRESS:
        raise ValueError(
            f"Yalnızca IN_PROGRESS batch tamamlanabilir. Mevcut: {batch.status}."
        )

    batch.actual_quantity = (
        actual_quantity
        if actual_quantity is not None
        else batch.planned_quantity
    )
    batch.waste_quantity = waste_quantity
    batch.status = ProductionBatchStatus.COMPLETED
    batch.completed_at = timezone.now()
    batch.save(
        update_fields=[
            "actual_quantity",
            "waste_quantity",
            "status",
            "completed_at",
            "updated_at",
        ]
    )

    # Siparişin tüm batch'leri tamamlandı mı?
    if batch.order_line_id:
        order = batch.order_line.order
        has_remaining = ProductionBatch.objects.filter(
            order_line__order=order
        ).exclude(
            status__in=[
                ProductionBatchStatus.COMPLETED,
                ProductionBatchStatus.CANCELLED,
            ]
        ).exists()

        if not has_remaining:
            _finalize_order_consumption(order, actor=actor)

    # Planın tüm batch'leri tamamlandı mı?
    has_pending_in_plan = ProductionBatch.objects.filter(
        plan=batch.plan
    ).exclude(
        status__in=[
            ProductionBatchStatus.COMPLETED,
            ProductionBatchStatus.CANCELLED,
        ]
    ).exists()

    if not has_pending_in_plan:
        plan = batch.plan
        plan.status = ProductionPlanStatus.COMPLETED
        plan.completed_at = timezone.now()
        plan.save(update_fields=["status", "completed_at", "updated_at"])

    return batch


@transaction.atomic
def cancel_batch(*, batch_id, reason: str = "", actor=None) -> ProductionBatch:
    """
    PLANNED/IN_PROGRESS → CANCELLED.

    NOT: Bu servis **order iptal etmez**. Siparişin rezervasyonları
    serbest bırakılmalıysa ayrıca `cancel_order` çağırın.
    """
    batch = _get_locked_batch(batch_id)

    if batch.status not in (
        ProductionBatchStatus.PLANNED,
        ProductionBatchStatus.IN_PROGRESS,
    ):
        raise ValueError(
            f"Yalnızca PLANNED/IN_PROGRESS batch iptal edilebilir. Mevcut: {batch.status}."
        )

    batch.status = ProductionBatchStatus.CANCELLED
    batch.completed_at = timezone.now()
    if reason:
        batch.notes = f"{batch.notes}\nCancelled: {reason}".strip()
    batch.save(update_fields=["status", "completed_at", "notes", "updated_at"])

    return batch


# ---------------------------------------------------------------------------
# Internal: tamamlanmış siparişin rezervasyonlarını consume et
# ---------------------------------------------------------------------------
def _finalize_order_consumption(order, actor=None) -> None:
    """
    Aktif rezervasyonları consume eder ve BatchIngredient satırları yazar.
    Idempotent: aktif rezervasyon yoksa no-op.
    """
    primary = (
        ProductionBatch.objects.filter(
            order_line__order=order,
            status=ProductionBatchStatus.COMPLETED,
        )
        .order_by("created_at")
        .first()
    )
    if not primary:
        return

    reservations = (
        StockReservation.objects.filter(
            order_id=order.id,
            status=ReservationStatus.ACTIVE,
        )
        .select_related("lot", "lot__ingredient", "lot__ingredient__base_unit")
    )

    for res in reservations:
        consume(reservation_id=res.id, actor=actor)
        BatchIngredient.objects.create(
            batch=primary,
            lot=res.lot,
            actual_quantity=res.quantity,
            unit=res.lot.ingredient.base_unit,
        )