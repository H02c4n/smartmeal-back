"""
Teslimat servisleri. Paketlerin run'lara atanması ve tamamlanması.
"""
from django.db import transaction
from django.utils import timezone

from apps.delivery.models import (
    DeliveryRun,
    DeliveryRunStatus,
    DeliveryStop,
    DeliveryStopStatus,
)
from apps.packing.models import Package, PackageStatus


def _get_active_stop_for_package(package_id):
    return DeliveryStop.objects.filter(
        package_id=package_id,
        status__in=[DeliveryStopStatus.PENDING, DeliveryStopStatus.DELIVERED],
    ).first()


@transaction.atomic
def create_run(
    *,
    delivery_date,
    driver=None,
    notes: str = "",
    actor=None,
) -> DeliveryRun:
    """Yeni DeliveryRun (PLANNED)."""
    return DeliveryRun.objects.create(
        delivery_date=delivery_date,
        driver=driver,
        notes=notes,
    )


@transaction.atomic
def assign_stop(
    *,
    run_id,
    package_id,
    sequence: int,
    actor=None,
) -> DeliveryStop:
    """
    READY_FOR_DELIVERY paketi bir run'a atar.

    Kurallar:
    - Run PLANNED olmalı (IN_PROGRESS/completed'a atama yapılamaz)
    - Package READY_FOR_DELIVERY olmalı
    - Package aktif bir durakta olmamalı
    - sequence > 0
    """
    run = DeliveryRun.objects.select_for_update().get(pk=run_id)
    if run.status != DeliveryRunStatus.PLANNED:
        raise ValueError(
            f"Yalnızca PLANNED run'a durak atanabilir. Mevcut: {run.status}."
        )

    if sequence <= 0:
        raise ValueError("sequence > 0 olmalı.")

    package = Package.objects.select_for_update().get(pk=package_id)
    if package.status != PackageStatus.READY_FOR_DELIVERY:
        raise ValueError(
            f"Paket READY_FOR_DELIVERY değil. Mevcut: {package.status}."
        )

    if _get_active_stop_for_package(package.id):
        raise ValueError(
            f"Paket {package.id} zaten aktif bir teslimat durağında."
        )

    return DeliveryStop.objects.create(
        run=run,
        package=package,
        sequence=sequence,
        status=DeliveryStopStatus.PENDING,
    )


@transaction.atomic
def start_run(*, run_id, actor=None) -> DeliveryRun:
    """PLANNED → IN_PROGRESS. En az 1 durak olmalı."""
    run = DeliveryRun.objects.select_for_update().get(pk=run_id)
    if run.status != DeliveryRunStatus.PLANNED:
        raise ValueError(
            f"Yalnızca PLANNED run başlatılabilir. Mevcut: {run.status}."
        )
    if not run.stops.exists():
        raise ValueError("Run'da hiç durak yok.")

    run.status = DeliveryRunStatus.IN_PROGRESS
    run.started_at = timezone.now()
    run.save(update_fields=["status", "started_at", "updated_at"])
    return run


@transaction.atomic
def complete_stop(
    *,
    stop_id,
    proof_reference: str = "",
    actor=None,
) -> DeliveryStop:
    """PENDING → DELIVERED. Package → DELIVERED. Run IN_PROGRESS olmalı."""
    stop = DeliveryStop.objects.select_for_update().select_related("run", "package").get(pk=stop_id)

    if stop.status != DeliveryStopStatus.PENDING:
        raise ValueError(
            f"Sadece PENDING durak tamamlanabilir. Mevcut: {stop.status}."
        )
    if stop.run.status != DeliveryRunStatus.IN_PROGRESS:
        raise ValueError(
            f"Run IN_PROGRESS değil. Mevcut: {stop.run.status}."
        )

    stop.status = DeliveryStopStatus.DELIVERED
    stop.delivered_at = timezone.now()
    stop.proof_reference = proof_reference
    stop.save(
        update_fields=["status", "delivered_at", "proof_reference", "updated_at"]
    )

    # Package DELIVERED
    package = Package.objects.select_for_update().get(pk=stop.package_id)
    if package.status == PackageStatus.READY_FOR_DELIVERY:
        package.status = PackageStatus.DELIVERED
        package.save(update_fields=["status", "updated_at"])

    _maybe_finalize_run(stop.run_id)
    return stop


@transaction.atomic
def fail_stop(
    *,
    stop_id,
    reason: str,
    actor=None,
) -> DeliveryStop:
    """
    PENDING → FAILED. Package READY_FOR_DELIVERY'da kalır
    (başka bir run'a atanabilmesi için).
    """
    stop = DeliveryStop.objects.select_for_update().select_related("run").get(pk=stop_id)

    if stop.status != DeliveryStopStatus.PENDING:
        raise ValueError(
            f"Sadece PENDING durak fail edilebilir. Mevcut: {stop.status}."
        )
    if stop.run.status != DeliveryRunStatus.IN_PROGRESS:
        raise ValueError(
            f"Run IN_PROGRESS değil. Mevcut: {stop.run.status}."
        )
    if not reason.strip():
        raise ValueError("fail için reason zorunlu.")

    stop.status = DeliveryStopStatus.FAILED
    stop.failure_reason = reason
    stop.save(update_fields=["status", "failure_reason", "updated_at"])

    # Package'a dokunmuyoruz — READY_FOR_DELIVERY kalsın
    _maybe_finalize_run(stop.run_id)
    return stop


@transaction.atomic
def cancel_run(*, run_id, reason: str = "", actor=None) -> DeliveryRun:
    """PLANNED/IN_PROGRESS → CANCELLED. PENDING duraklar FAILED'a alınır."""
    run = DeliveryRun.objects.select_for_update().get(pk=run_id)
    if run.status in (
        DeliveryRunStatus.COMPLETED,
        DeliveryRunStatus.CANCELLED,
    ):
        raise ValueError(
            f"Bu run iptal edilemez. Mevcut: {run.status}."
        )

    pending = run.stops.filter(status=DeliveryStopStatus.PENDING)
    for stop in pending:
        stop.status = DeliveryStopStatus.FAILED
        stop.failure_reason = f"Run cancelled: {reason}".strip()
        stop.save(update_fields=["status", "failure_reason", "updated_at"])

    run.status = DeliveryRunStatus.CANCELLED
    if reason:
        run.notes = f"{run.notes}\nCancelled: {reason}".strip()
    run.save(update_fields=["status", "notes", "updated_at"])
    return run


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------
def _maybe_finalize_run(run_id) -> None:
    """PENDING durak kalmadıysa run COMPLETED."""
    if DeliveryStop.objects.filter(
        run_id=run_id, status=DeliveryStopStatus.PENDING
    ).exists():
        return
    run = DeliveryRun.objects.select_for_update().get(pk=run_id)
    if run.status != DeliveryRunStatus.IN_PROGRESS:
        return
    run.status = DeliveryRunStatus.COMPLETED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at", "updated_at"])