"""Incident lifecycle servisleri testleri."""
import pytest

from apps.accounts.models import User
from apps.quality.models import (
    QualityIncident,
    QualityIncidentSeverity,
    QualityIncidentStatus,
)
from apps.quality.services.incidents import (
    close_incident,
    hold_batch,
    hold_incident,
    raise_incident,
    release_incident,
)

from apps.quality.tests.fixtures import make_batch


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="a@x.com", password="x")


@pytest.mark.django_db
class TestRaiseIncident:
    def test_creates_open(self):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id,
            severity=QualityIncidentSeverity.LOW,
            reason="note",
        )
        assert inc.status == QualityIncidentStatus.OPEN
        assert inc.batch_id == batch.id

    def test_empty_reason_rejected(self):
        batch = make_batch()
        with pytest.raises(ValueError, match="reason"):
            raise_incident(
                batch_id=batch.id,
                severity=QualityIncidentSeverity.LOW,
                reason="   ",
            )

    def test_invalid_severity_rejected(self):
        batch = make_batch()
        with pytest.raises(ValueError, match="severity"):
            raise_incident(
                batch_id=batch.id,
                severity="NOT_VALID",
                reason="x",
            )


@pytest.mark.django_db
class TestHoldRelease:
    def test_hold_transitions_open_to_on_hold(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id,
            severity=QualityIncidentSeverity.HIGH,
            reason="temp",
        )
        held = hold_incident(incident_id=inc.id, actor=admin)
        assert held.status == QualityIncidentStatus.ON_HOLD

    def test_hold_twice_fails(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="HIGH", reason="x"
        )
        hold_incident(incident_id=inc.id, actor=admin)
        with pytest.raises(ValueError, match="OPEN"):
            hold_incident(incident_id=inc.id, actor=admin)

    def test_release_transitions_to_released(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="HIGH", reason="x"
        )
        hold_incident(incident_id=inc.id, actor=admin)
        released = release_incident(
            incident_id=inc.id, resolver=admin, notes="fixed"
        )
        assert released.status == QualityIncidentStatus.RELEASED
        assert released.resolved_by_id == admin.id
        assert released.resolved_at is not None
        assert released.resolution_notes == "fixed"

    def test_release_open_incident_fails(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="HIGH", reason="x"
        )
        with pytest.raises(ValueError, match="ON_HOLD"):
            release_incident(incident_id=inc.id, resolver=admin)

    def test_close_from_open(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="LOW", reason="x"
        )
        closed = close_incident(incident_id=inc.id, resolver=admin, notes="ok")
        assert closed.status == QualityIncidentStatus.CLOSED

    def test_close_from_on_hold(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="HIGH", reason="x"
        )
        hold_incident(incident_id=inc.id, actor=admin)
        closed = close_incident(incident_id=inc.id, resolver=admin)
        assert closed.status == QualityIncidentStatus.CLOSED

    def test_close_released_fails(self, admin):
        batch = make_batch()
        inc = raise_incident(
            batch_id=batch.id, severity="HIGH", reason="x"
        )
        hold_incident(incident_id=inc.id, actor=admin)
        release_incident(incident_id=inc.id, resolver=admin)
        with pytest.raises(ValueError, match="kapanmış"):
            close_incident(incident_id=inc.id, resolver=admin)


@pytest.mark.django_db
class TestShortcuts:
    def test_hold_batch_creates_on_hold_directly(self):
        batch = make_batch()
        inc = hold_batch(batch_id=batch.id, reason="temp spike")
        assert inc.status == QualityIncidentStatus.ON_HOLD
        assert inc.batch_id == batch.id

    def test_hold_lot_creates_on_hold_directly(self):
        from apps.inventory.tests.fixtures import make_lot

        lot = make_lot()
        inc = hold_batch  # type: ignore # to avoid unused import warning
        from apps.quality.services.incidents import hold_lot

        inc = hold_lot(lot_id=lot.id, reason="mold")
        assert inc.status == QualityIncidentStatus.ON_HOLD
        assert inc.lot_id == lot.id