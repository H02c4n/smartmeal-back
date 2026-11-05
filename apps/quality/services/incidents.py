"""
Uygunsuzluk yaşam döngüsü. State machine:

    OPEN ──hold──▶ ON_HOLD ──release──▶ RELEASED
      │               │
      └───close───┬───┘
                  ▼
                CLOSED

- OPEN: takip ediliyor, akışa engel değil
- ON_HOLD: parti/lot paketleme/teslimata gidemez
- RELEASED / CLOSED: kapanmış
"""
from django.db import transaction
from django.utils import timezone

from apps.quality.models import (
    QualityIncident,
    QualityIncidentSeverity,
    QualityIncidentStatus,
)


@transaction.atomic
def raise_incident(
    *,
    severity: str,
    reason: str,
    batch_id=None,
    lot_id=None,
    actor=None,
) -> QualityIncident:
    """OPEN durumunda yeni uygunsuzluk. Akışı bloklamaz."""
    if batch_id is None and lot_id is None:
        raise ValueError("batch_id veya lot_id zorunlu.")
    if batch_id is not None and lot_id is not None:
        raise ValueError("Sadece biri verilmeli.")
    if not reason.strip():
        raise ValueError("reason zorunlu.")
    if severity not in QualityIncidentSeverity.values:
        raise ValueError(f"Geçersiz severity: {severity}")

    return QualityIncident.objects.create(
        batch_id=batch_id,
        lot_id=lot_id,
        severity=severity,
        reason=reason,
        status=QualityIncidentStatus.OPEN,
        reported_by=actor,
    )


@transaction.atomic
def hold_incident(*, incident_id, actor=None) -> QualityIncident:
    """OPEN → ON_HOLD. Parti/lot artık kullanılamaz."""
    inc = QualityIncident.objects.select_for_update().get(pk=incident_id)
    if inc.status != QualityIncidentStatus.OPEN:
        raise ValueError(
            f"Sadece OPEN incident hold'a alınabilir. Mevcut: {inc.status}."
        )
    inc.status = QualityIncidentStatus.ON_HOLD
    inc.save(update_fields=["status"])
    return inc


@transaction.atomic
def release_incident(*, incident_id, resolver, notes: str = "") -> QualityIncident:
    """ON_HOLD → RELEASED. Gate tekrar açılır."""
    if resolver is None or not getattr(resolver, "is_authenticated", False):
        raise ValueError("Release için yetkili kullanıcı (resolver) zorunlu.")

    inc = QualityIncident.objects.select_for_update().get(pk=incident_id)
    if inc.status != QualityIncidentStatus.ON_HOLD:
        raise ValueError(
            f"Sadece ON_HOLD incident release edilebilir. Mevcut: {inc.status}."
        )
    inc.status = QualityIncidentStatus.RELEASED
    inc.resolved_by = resolver
    inc.resolved_at = timezone.now()
    inc.resolution_notes = notes
    inc.save(
        update_fields=[
            "status",
            "resolved_by",
            "resolved_at",
            "resolution_notes",
        ]
    )
    return inc


@transaction.atomic
def close_incident(*, incident_id, resolver, notes: str = "") -> QualityIncident:
    """OPEN veya ON_HOLD → CLOSED. Release yerine "kapat" (nihai)."""
    if resolver is None or not getattr(resolver, "is_authenticated", False):
        raise ValueError("Close için yetkili kullanıcı (resolver) zorunlu.")

    inc = QualityIncident.objects.select_for_update().get(pk=incident_id)
    if inc.status in (
        QualityIncidentStatus.RELEASED,
        QualityIncidentStatus.CLOSED,
    ):
        raise ValueError(f"Zaten kapanmış. Mevcut: {inc.status}.")

    inc.status = QualityIncidentStatus.CLOSED
    inc.resolved_by = resolver
    inc.resolved_at = timezone.now()
    inc.resolution_notes = notes
    inc.save(
        update_fields=[
            "status",
            "resolved_by",
            "resolved_at",
            "resolution_notes",
        ]
    )
    return inc


# ---------------------------------------------------------------------------
# Shortcuts: direkt bloklamak için tek çağrı
# ---------------------------------------------------------------------------
@transaction.atomic
def hold_batch(
    *,
    batch_id,
    reason: str,
    severity: str = QualityIncidentSeverity.HIGH,
    actor=None,
) -> QualityIncident:
    """Batch için tek çağrıda ON_HOLD incident."""
    inc = raise_incident(
        batch_id=batch_id, severity=severity, reason=reason, actor=actor
    )
    return hold_incident(incident_id=inc.id, actor=actor)


@transaction.atomic
def hold_lot(
    *,
    lot_id,
    reason: str,
    severity: str = QualityIncidentSeverity.HIGH,
    actor=None,
) -> QualityIncident:
    """Lot için tek çağrıda ON_HOLD incident."""
    inc = raise_incident(
        lot_id=lot_id, severity=severity, reason=reason, actor=actor
    )
    return hold_incident(incident_id=inc.id, actor=actor)