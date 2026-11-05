"""is_batch_releasable / is_lot_releasable gate testleri."""
import pytest

from apps.accounts.models import User
from apps.quality.services.incidents import (
    hold_batch,
    hold_incident,
    raise_incident,
    release_incident,
)
from apps.quality.services.status import is_batch_releasable, is_lot_releasable

from apps.quality.tests.fixtures import make_batch


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="a@x.com", password="x")


@pytest.mark.django_db
class TestBatchReleasable:
    def test_no_incidents_means_releasable(self):
        batch = make_batch()
        assert is_batch_releasable(batch.id) is True

    def test_open_incident_blocks(self):
        batch = make_batch()
        raise_incident(batch_id=batch.id, severity="LOW", reason="x")
        assert is_batch_releasable(batch.id) is False

    def test_on_hold_incident_blocks(self):
        batch = make_batch()
        hold_batch(batch_id=batch.id, reason="x")
        assert is_batch_releasable(batch.id) is False

    def test_released_incident_does_not_block(self, admin):
        batch = make_batch()
        inc = raise_incident(batch_id=batch.id, severity="HIGH", reason="x")
        hold_incident(incident_id=inc.id, actor=admin)
        release_incident(incident_id=inc.id, resolver=admin)
        assert is_batch_releasable(batch.id) is True


@pytest.mark.django_db
class TestLotReleasable:
    def test_no_incidents_means_releasable(self):
        from apps.inventory.tests.fixtures import make_lot

        lot = make_lot()
        assert is_lot_releasable(lot.id) is True

    def test_on_hold_incident_blocks(self):
        from apps.inventory.tests.fixtures import make_lot
        from apps.quality.services.incidents import hold_lot

        lot = make_lot()
        hold_lot(lot_id=lot.id, reason="x")
        assert is_lot_releasable(lot.id) is False