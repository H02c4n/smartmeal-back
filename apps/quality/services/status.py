"""Gate: parti/lot paketleme ve teslimata hazır mı?"""
from apps.quality.models import QualityIncident, QualityIncidentStatus

BLOCKING_STATUSES = (
    QualityIncidentStatus.OPEN,
    QualityIncidentStatus.ON_HOLD,
)


def is_batch_releasable(batch_id) -> bool:
    """Açık veya hold'daki incident yoksa True."""
    return not QualityIncident.objects.filter(
        batch_id=batch_id, status__in=BLOCKING_STATUSES
    ).exists()


def is_lot_releasable(lot_id) -> bool:
    """Açık veya hold'daki incident yoksa True."""
    return not QualityIncident.objects.filter(
        lot_id=lot_id, status__in=BLOCKING_STATUSES
    ).exists()