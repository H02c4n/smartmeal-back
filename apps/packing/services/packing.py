"""
Paketleme servisleri. Kalite gate'i burada uygulanır: bir batch
paketlenebilmesi için hem COMPLETED olmalı hem de açık/hold'da
quality incident'ı olmamalı.
"""
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus
from apps.packing.models import Package, PackageLine, PackageStatus
from apps.production.models import ProductionBatch, ProductionBatchStatus
from apps.quality.services.status import is_batch_releasable

_MAX_CODE_ATTEMPTS = 3


def _generate_package_code() -> str:
    prefix = f"PKG-{timezone.now():%Y%m%d}-"
    last = (
        Package.objects.filter(package_code__startswith=prefix)
        .order_by("-package_code")
        .values_list("package_code", flat=True)
        .first()
    )
    if last:
        seq = int(last.rsplit("-", 1)[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _get_active_package(order: Order) -> Package | None:
    return (
        Package.objects.filter(order=order)
        .exclude(status=PackageStatus.CANCELLED)
        .order_by("-created_at")
        .first()
    )


@transaction.atomic
def pack_order(*, order_id, actor=None, notes: str = "") -> Package:
    """
    Bir siparişin tüm batch'lerini tek pakette toplar.

    Kurallar:
    - Sipariş CONFIRMED olmalı
    - Tüm batch'ler COMPLETED olmalı
    - Her batch is_batch_releasable() olmalı (kalite gate)
    - Idempotent: aktif paket varsa döner
    """
    order = Order.objects.select_for_update().get(pk=order_id)

    if order.status != OrderStatus.CONFIRMED:
        raise ValueError(
            f"Sipariş paketlenebilir durumda değil: {order.status}."
        )

    existing = _get_active_package(order)
    if existing:
        return existing  # idempotent

    batches = list(
        ProductionBatch.objects.filter(order_line__order=order).select_related(
            "product"
        )
    )
    if not batches:
        raise ValueError("Sipariş için üretim partisi yok.")

    # Kalite gate + durum kontrolü
    for batch in batches:
        if batch.status != ProductionBatchStatus.COMPLETED:
            raise ValueError(
                f"Batch {batch.id} tamamlanmamış: {batch.status}."
            )
        if not is_batch_releasable(batch.id):
            raise ValueError(
                f"Batch {batch.id} kalite onayından geçmedi (açık incident var)."
            )

    # Kod üret — race için retry
    package = None
    for attempt in range(_MAX_CODE_ATTEMPTS):
        try:
            with transaction.atomic():
                package = Package.objects.create(
                    order=order,
                    package_code=_generate_package_code(),
                    status=PackageStatus.PACKED,
                    packed_by=actor,
                    packed_at=timezone.now(),
                    notes=notes,
                )
            break
        except IntegrityError:
            if attempt == _MAX_CODE_ATTEMPTS - 1:
                raise

    # Satırlar
    for batch in batches:
        PackageLine.objects.create(
            package=package,
            batch=batch,
            quantity=batch.actual_quantity or batch.planned_quantity,
        )

    return package


@transaction.atomic
def mark_ready_for_delivery(*, package_id, actor=None) -> Package:
    """PACKED → READY_FOR_DELIVERY. Faz 6 delivery akışı için hazırlık."""
    package = Package.objects.select_for_update().get(pk=package_id)
    if package.status != PackageStatus.PACKED:
        raise ValueError(
            f"Yalnızca PACKED paket READY_FOR_DELIVERY yapılabilir. "
            f"Mevcut: {package.status}."
        )
    package.status = PackageStatus.READY_FOR_DELIVERY
    package.save(update_fields=["status", "updated_at"])
    return package


@transaction.atomic
def cancel_package(*, package_id, reason: str = "", actor=None) -> Package:
    """PACKED/READY_FOR_DELIVERY → CANCELLED. DELIVERED iptal edilemez."""
    package = Package.objects.select_for_update().get(pk=package_id)
    if package.status in (
        PackageStatus.CANCELLED,
        PackageStatus.DELIVERED,
    ):
        raise ValueError(
            f"Bu paket iptal edilemez. Mevcut: {package.status}."
        )
    package.status = PackageStatus.CANCELLED
    if reason:
        package.notes = f"{package.notes}\nCancelled: {reason}".strip()
    package.save(update_fields=["status", "notes", "updated_at"])
    return package