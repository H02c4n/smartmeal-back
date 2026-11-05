"""Quality check kayıt servisi."""
from decimal import Decimal

from django.db import transaction

from apps.quality.models import (
    QualityCheck,
    QualityCheckResult,
    QualityCheckType,
)


@transaction.atomic
def record_check(
    *,
    check_type: str,
    result: str,
    batch_id=None,
    lot_id=None,
    measurement_value: Decimal | None = None,
    measurement_unit: str = "",
    notes: str = "",
    actor=None,
) -> QualityCheck:
    """
    Bir parti veya lot için tek bir ölçüm kaydeder.

    Kurallar:
    - Sadece biri (batch_id veya lot_id) verilmeli.
    - check_type geçerli bir enum değeri olmalı.
    - result PASS/FAIL.
    - measurement_value varsa measurement_unit zorunlu.
    """
    if batch_id is None and lot_id is None:
        raise ValueError("batch_id veya lot_id zorunlu.")
    if batch_id is not None and lot_id is not None:
        raise ValueError("Sadece biri (batch_id veya lot_id) verilmeli.")

    if check_type not in QualityCheckType.values:
        raise ValueError(f"Geçersiz check_type: {check_type}")
    if result not in QualityCheckResult.values:
        raise ValueError(f"Geçersiz result: {result}")
    if measurement_value is not None and not measurement_unit.strip():
        raise ValueError("measurement_unit zorunlu (ölçüm değeri varsa).")

    return QualityCheck.objects.create(
        batch_id=batch_id,
        lot_id=lot_id,
        check_type=check_type,
        result=result,
        measurement_value=measurement_value,
        measurement_unit=measurement_unit,
        notes=notes,
        checked_by=actor,
    )