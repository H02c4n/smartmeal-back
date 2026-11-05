"""QualityIncident model testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.quality.models import (
    QualityIncident,
    QualityIncidentSeverity,
    QualityIncidentStatus,
)

from apps.quality.tests.fixtures import make_batch


@pytest.mark.django_db
class TestQualityIncident:
    def test_create_incident_defaults(self):
        batch = make_batch()
        inc = QualityIncident.objects.create(
            batch=batch,
            severity=QualityIncidentSeverity.HIGH,
            reason="Temperature spike detected",
        )
        assert inc.status == QualityIncidentStatus.OPEN
        assert inc.resolved_at is None
        assert "HIGH" in str(inc)

    def test_lot_incident(self):
        from apps.inventory.tests.fixtures import make_lot

        lot = make_lot()
        inc = QualityIncident.objects.create(
            lot=lot,
            severity=QualityIncidentSeverity.CRITICAL,
            reason="Mold detected",
        )
        assert inc.status == QualityIncidentStatus.OPEN

    def test_both_batch_and_lot_rejected(self):
        from apps.inventory.tests.fixtures import make_lot

        batch = make_batch()
        lot = make_lot()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                QualityIncident.objects.create(
                    batch=batch,
                    lot=lot,
                    severity="HIGH",
                    reason="x",
                )