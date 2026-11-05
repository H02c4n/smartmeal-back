"""create_order servis testleri."""
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.orders.models import Order, OrderStatus
from apps.orders.services.order import create_order

from apps.orders.tests.fixtures import VALID_ADDRESS, make_approved_recipe, make_customer, make_product


@pytest.mark.django_db
class TestCreateOrder:
    def test_creates_order_with_one_line(self):
        customer = make_customer()
        product = make_product(price="89.00")
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 3}],
        )
        assert order.status == OrderStatus.PLACED
        assert order.order_number.startswith(f"SM-{timezone.now():%Y%m%d}-")
        assert order.lines.count() == 1
        line = order.lines.first()
        assert line.product_name_snapshot == product.name
        assert line.unit_price_snapshot == Decimal("89.00")
        assert line.line_total == Decimal("267.00")
        assert order.subtotal == Decimal("267.00")
        assert order.total_amount == Decimal("267.00")

    def test_snapshots_recipe_version(self):
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        line = order.lines.first()
        assert line.recipe_version_snapshot_id == recipe.id

    def test_no_recipe_leaves_snapshot_null(self):
        customer = make_customer()
        product = make_product()  # no approved recipe
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        assert order.lines.first().recipe_version_snapshot_id is None

    def test_multiple_products(self):
        customer = make_customer()
        p1 = make_product(sku="P1", price="100.00")
        p2 = make_product(sku="P2", price="50.00")
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[
                {"product_id": p1.id, "quantity": 2},
                {"product_id": p2.id, "quantity": 3},
            ],
        )
        assert order.lines.count() == 2
        assert order.subtotal == Decimal("350.00")  # 200 + 150

    def test_same_product_twice_merged(self):
        customer = make_customer()
        p = make_product(price="100.00")
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[
                {"product_id": p.id, "quantity": 1},
                {"product_id": p.id, "quantity": 2},
            ],
        )
        assert order.lines.count() == 1
        assert order.lines.first().quantity == 3
        assert order.subtotal == Decimal("300.00")

    def test_empty_items_rejected(self):
        customer = make_customer()
        with pytest.raises(ValueError, match="en az bir"):
            create_order(
                customer=customer,
                delivery_date=timezone.now().date(),
                delivery_address=VALID_ADDRESS,
                items=[],
            )

    def test_zero_quantity_rejected(self):
        customer = make_customer()
        p = make_product()
        with pytest.raises(ValueError, match="Geçersiz satır"):
            create_order(
                customer=customer,
                delivery_date=timezone.now().date(),
                delivery_address=VALID_ADDRESS,
                items=[{"product_id": p.id, "quantity": 0}],
            )

    def test_inactive_product_rejected(self):
        customer = make_customer()
        p = make_product()
        p.is_active = False
        p.save()
        with pytest.raises(ValueError, match="pasif"):
            create_order(
                customer=customer,
                delivery_date=timezone.now().date(),
                delivery_address=VALID_ADDRESS,
                items=[{"product_id": p.id, "quantity": 1}],
            )

    def test_missing_address_field_rejected(self):
        customer = make_customer()
        p = make_product()
        with pytest.raises(ValueError, match="Adres eksik"):
            create_order(
                customer=customer,
                delivery_date=timezone.now().date(),
                delivery_address={"street_address": "X", "city": "Y"},
                items=[{"product_id": p.id, "quantity": 1}],
            )

    def test_order_numbers_increment(self):
        customer = make_customer()
        p = make_product()
        today = timezone.now().date()
        o1 = create_order(
            customer=customer, delivery_date=today,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": p.id, "quantity": 1}],
        )
        o2 = create_order(
            customer=customer, delivery_date=today,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": p.id, "quantity": 1}],
        )
        n1 = int(o1.order_number.rsplit("-", 1)[-1])
        n2 = int(o2.order_number.rsplit("-", 1)[-1])
        assert n2 == n1 + 1