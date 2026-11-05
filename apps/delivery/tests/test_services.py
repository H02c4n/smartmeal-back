"""Delivery servisleri testleri."""
import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.delivery.models import (
    DeliveryRun,
    DeliveryRunStatus,
    DeliveryStop,
    DeliveryStopStatus,
)
from apps.delivery.services.delivery import (
    assign_stop,
    cancel_run,
    complete_stop,
    create_run,
    fail_stop,
    start_run,
)
from apps.packing.models import Package, PackageStatus
from apps.packing.tests.fixtures import make_ready_package


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="admin@x.com", password="x")


@pytest.mark.django_db
class TestAssignStop:
    def test_assign_ready_package(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        assert stop.status == DeliveryStopStatus.PENDING
        assert stop.package_id == pkg.id

    def test_assign_non_ready_package_rejected(self, admin):
        # PACKED (henüz READY değil) → hata
        from apps.production.tests.fixtures import make_completed_batch
        from apps.packing.services.packing import pack_order
        order, _ = make_completed_batch(qty=1)
        pkg = pack_order(order_id=order.id, actor=admin)
        assert pkg.status == PackageStatus.PACKED

        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        with pytest.raises(ValueError, match="READY_FOR_DELIVERY"):
            assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)

    def test_assign_same_package_twice_rejected(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run1 = create_run(delivery_date=timezone.now().date(), actor=admin)
        run2 = create_run(delivery_date=timezone.now().date(), actor=admin)
        assign_stop(run_id=run1.id, package_id=pkg.id, sequence=1)
        with pytest.raises(ValueError, match="zaten aktif"):
            assign_stop(run_id=run2.id, package_id=pkg.id, sequence=1)

    def test_assign_to_started_run_rejected(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)
        pkg2, _, _ = make_ready_package(actor=admin)
        with pytest.raises(ValueError, match="PLANNED"):
            assign_stop(run_id=run.id, package_id=pkg2.id, sequence=2)


@pytest.mark.django_db
class TestStartRun:
    def test_start_with_stops(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        started = start_run(run_id=run.id, actor=admin)
        assert started.status == DeliveryRunStatus.IN_PROGRESS
        assert started.started_at is not None

    def test_start_empty_run_rejected(self, admin):
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        with pytest.raises(ValueError, match="durak yok"):
            start_run(run_id=run.id, actor=admin)


@pytest.mark.django_db
class TestCompleteStop:
    def test_complete_marks_package_delivered(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)

        completed = complete_stop(stop_id=stop.id, proof_reference="photo.jpg", actor=admin)
        assert completed.status == DeliveryStopStatus.DELIVERED
        assert completed.proof_reference == "photo.jpg"

        pkg.refresh_from_db()
        assert pkg.status == PackageStatus.DELIVERED

    def test_complete_when_run_not_started_rejected(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            complete_stop(stop_id=stop.id, actor=admin)

    def test_last_stop_completes_run(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)
        complete_stop(stop_id=stop.id, actor=admin)

        run.refresh_from_db()
        assert run.status == DeliveryRunStatus.COMPLETED
        assert run.completed_at is not None


@pytest.mark.django_db
class TestFailStop:
    def test_fail_keeps_package_ready(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)

        failed = fail_stop(stop_id=stop.id, reason="customer absent", actor=admin)
        assert failed.status == DeliveryStopStatus.FAILED
        assert failed.failure_reason == "customer absent"

        pkg.refresh_from_db()
        assert pkg.status == PackageStatus.READY_FOR_DELIVERY

    def test_fail_then_reassign_to_new_run(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run1 = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop1 = assign_stop(run_id=run1.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run1.id, actor=admin)
        fail_stop(stop_id=stop1.id, reason="absent", actor=admin)

        # Aynı paket başka run'a atanabilmeli
        run2 = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop2 = assign_stop(run_id=run2.id, package_id=pkg.id, sequence=1)
        assert stop2.status == DeliveryStopStatus.PENDING

    def test_fail_requires_reason(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)
        with pytest.raises(ValueError, match="reason"):
            fail_stop(stop_id=stop.id, reason="   ", actor=admin)


@pytest.mark.django_db
class TestCancelRun:
    def test_cancel_planned_run(self, admin):
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        cancelled = cancel_run(run_id=run.id, reason="weather", actor=admin)
        assert cancelled.status == DeliveryRunStatus.CANCELLED

    def test_cancel_fails_pending_stops(self, admin):
        pkg, _, _ = make_ready_package(actor=admin)
        run = create_run(delivery_date=timezone.now().date(), actor=admin)
        stop = assign_stop(run_id=run.id, package_id=pkg.id, sequence=1)
        start_run(run_id=run.id, actor=admin)
        cancel_run(run_id=run.id, reason="accident", actor=admin)

        stop.refresh_from_db()
        assert stop.status == DeliveryStopStatus.FAILED
        assert "Run cancelled" in stop.failure_reason

        pkg.refresh_from_db()
        assert pkg.status == PackageStatus.READY_FOR_DELIVERY