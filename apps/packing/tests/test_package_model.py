"""Package ve PackageLine model testleri."""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.packing.models import Package, PackageLine, PackageStatus
from apps.production.tests.fixtures import make_completed_batch


@pytest.mark.django_db
class TestPackageModel:
    def test_create_defaults(self):
        order, _ = make_completed_batch()
        pkg = Package.objects.create(order=order, package_code="PKG-1")
        assert pkg.status == PackageStatus.PACKED
        assert pkg.packed_by is None
        assert str(pkg) == "PKG-1 [PACKED]"

    def test_package_code_unique(self):
        order1, _ = make_completed_batch()
        # aynı order için ikinci paket constraint'e çarpmadan yaratılamaz zaten
        # ama farklı order ile aynı kodu deneyelim
        from apps.orders.tests.fixtures import make_customer, make_product
        from apps.orders.services.order import create_order
        from apps.orders.tests.fixtures import VALID_ADDRESS
        from django.utils import timezone

        customer2 = make_customer("c2@x.com")
        product2 = make_product(sku="P2")
        order2 = create_order(
            customer=customer2,
            delivery_date=timezone.now().date() + timezone.timedelta(days=1),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product2.id, "quantity": 1}],
        )
        Package.objects.create(order=order1, package_code="PKG-DUP")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Package.objects.create(order=order2, package_code="PKG-DUP")


@pytest.mark.django_db
class TestPackageLineModel:
    def test_create(self):
        order, batch = make_completed_batch(qty=2)
        pkg = Package.objects.create(order=order, package_code="PKG-A")
        line = PackageLine.objects.create(
            package=pkg, batch=batch, quantity=2
        )
        assert line.quantity == 2

    def test_unique_package_batch(self):
        order, batch = make_completed_batch(qty=2)
        pkg = Package.objects.create(order=order, package_code="PKG-A")
        PackageLine.objects.create(package=pkg, batch=batch, quantity=2)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PackageLine.objects.create(
                    package=pkg, batch=batch, quantity=1
                )

    def test_quantity_must_be_positive(self):
        order, batch = make_completed_batch(qty=2)
        pkg = Package.objects.create(order=order, package_code="PKG-A")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PackageLine.objects.create(
                    package=pkg, batch=batch, quantity=0
                )