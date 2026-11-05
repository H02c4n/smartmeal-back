"""pack_order + mark_ready_for_delivery + cancel_package testleri."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.orders.models import OrderStatus
from apps.orders.services.fulfillment import confirm_order
from apps.orders.services.order import create_order
from apps.orders.tests.fixtures import (
    VALID_ADDRESS,
    make_approved_recipe,
    make_customer,
    make_product,
    make_released_lot,
)
from apps.packing.models import Package, PackageLine, PackageStatus
from apps.packing.services.packing import (
    cancel_package,
    mark_ready_for_delivery,
    pack_order,
)
from apps.production.models import ProductionBatch
from apps.production.services.execution import complete_batch, start_batch
from apps.production.services.planning import plan_batches_for_date
from apps.production.tests.fixtures import make_completed_batch
from apps.quality.services.incidents import hold_batch, raise_incident


@pytest.fixture
def admin():
    return User.objects.create_superuser(email="a@x.com", password="x")


@pytest.mark.django_db
class TestPackOrderHappyPath:
    def test_pack_completed_order(self, admin):
        order, batch = make_completed_batch(qty=2)
        pkg = pack_order(order_id=order.id, actor=admin)
        assert pkg.status == PackageStatus.PACKED
        assert pkg.package_code.startswith("PKG-")
        assert pkg.packed_by_id == admin.id
        assert pkg.packed_at is not None
        assert pkg.lines.count() == 1
        line = pkg.lines.first()
        assert line.batch_id == batch.id
        assert line.quantity == 2

    def test_package_code_sequential(self, admin):
        # İki farklı sipariş → ardışık kod
        order1, _ = make_completed_batch(qty=1)
        pkg1 = pack_order(order_id=order1.id, actor=admin)

        # İkinci sipariş için ayrı customer ve ürün gerek
        target = timezone.now().date() + timedelta(days=1)
        customer = make_customer("c2@x.com")
        product = make_product(sku="P2")
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        make_released_lot(ingredient=ing, qty=5000, code="LOT-2")
        order2 = create_order(
            customer=customer,
            delivery_date=target,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        confirm_order(order_id=order2.id)
        plan, _ = plan_batches_for_date(production_date=target)
        batch2 = ProductionBatch.objects.get(order_line__order=order2)
        start_batch(batch_id=batch2.id)
        complete_batch(batch_id=batch2.id, actual_quantity=1)

        pkg2 = pack_order(order_id=order2.id, actor=admin)

        n1 = int(pkg1.package_code.rsplit("-", 1)[-1])
        n2 = int(pkg2.package_code.rsplit("-", 1)[-1])
        assert n2 == n1 + 1


@pytest.mark.django_db
class TestPackOrderIdempotency:
    def test_second_call_returns_existing(self, admin):
        order, _ = make_completed_batch(qty=1)
        pkg1 = pack_order(order_id=order.id, actor=admin)
        pkg2 = pack_order(order_id=order.id, actor=admin)
        assert pkg1.id == pkg2.id
        assert Package.objects.filter(order=order).count() == 1


@pytest.mark.django_db
class TestPackOrderGateRejections:
    def test_order_not_confirmed_rejected(self):
        # PLACED sipariş → hata
        target = timezone.now().date() + timedelta(days=1)
        customer = make_customer()
        product = make_product()
        order = create_order(
            customer=customer,
            delivery_date=target,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        with pytest.raises(ValueError, match="paketlenebilir durumda değil"):
            pack_order(order_id=order.id)

    def test_order_without_batches_rejected(self):
        target = timezone.now().date() + timedelta(days=1)
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        make_released_lot(ingredient=ing, qty=5000)
        order = create_order(
            customer=customer,
            delivery_date=target,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        confirm_order(order_id=order.id)
        # plan oluşturulmadı → batch yok
        with pytest.raises(ValueError, match="üretim partisi yok"):
            pack_order(order_id=order.id)

    def test_batch_not_completed_rejected(self):
        # PLANNED batch
        target = timezone.now().date() + timedelta(days=1)
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        make_released_lot(ingredient=ing, qty=5000)
        order = create_order(
            customer=customer,
            delivery_date=target,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        confirm_order(order_id=order.id)
        plan_batches_for_date(production_date=target)
        with pytest.raises(ValueError, match="tamamlanmamış"):
            pack_order(order_id=order.id)

    def test_open_incident_blocks_packing(self):
        order, batch = make_completed_batch(qty=1)
        raise_incident(batch_id=batch.id, severity="LOW", reason="note")
        with pytest.raises(ValueError, match="kalite onayından geçmedi"):
            pack_order(order_id=order.id)

    def test_on_hold_incident_blocks_packing(self):
        order, batch = make_completed_batch(qty=1)
        hold_batch(batch_id=batch.id, reason="temp spike")
        with pytest.raises(ValueError, match="kalite onayından geçmedi"):
            pack_order(order_id=order.id)

    def test_released_incident_allows_packing(self, admin):
        order, batch = make_completed_batch(qty=1)
        inc = hold_batch(batch_id=batch.id, reason="temp spike")
        from apps.quality.services.incidents import release_incident
        release_incident(incident_id=inc.id, resolver=admin, notes="ok")
        pkg = pack_order(order_id=order.id, actor=admin)
        assert pkg.status == PackageStatus.PACKED


@pytest.mark.django_db
class TestStatusTransitions:
    def test_mark_ready_for_delivery(self, admin):
        order, _ = make_completed_batch(qty=1)
        pkg = pack_order(order_id=order.id, actor=admin)
        ready = mark_ready_for_delivery(package_id=pkg.id, actor=admin)
        assert ready.status == PackageStatus.READY_FOR_DELIVERY

    def test_mark_ready_twice_fails(self, admin):
        order, _ = make_completed_batch(qty=1)
        pkg = pack_order(order_id=order.id, actor=admin)
        mark_ready_for_delivery(package_id=pkg.id, actor=admin)
        with pytest.raises(ValueError, match="PACKED"):
            mark_ready_for_delivery(package_id=pkg.id, actor=admin)

    def test_cancel_packed_package(self, admin):
        order, _ = make_completed_batch(qty=1)
        pkg = pack_order(order_id=order.id, actor=admin)
        cancelled = cancel_package(package_id=pkg.id, reason="test", actor=admin)
        assert cancelled.status == PackageStatus.CANCELLED
        assert "Cancelled: test" in cancelled.notes

    def test_cancel_delivered_fails(self, admin):
        order, _ = make_completed_batch(qty=1)
        pkg = pack_order(order_id=order.id, actor=admin)
        # Manual: DELIVERED'a çek
        Package.objects.filter(pk=pkg.id).update(status=PackageStatus.DELIVERED)
        with pytest.raises(ValueError, match="iptal edilemez"):
            cancel_package(package_id=pkg.id, actor=admin)