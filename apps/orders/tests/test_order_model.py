"""Order ve OrderLine model testleri."""
from decimal import Decimal

import pytest

from apps.orders.models import Order, OrderLine, OrderStatus

from .fixtures import VALID_ADDRESS, make_customer, make_product


@pytest.mark.django_db
class TestOrderModel:
    def test_create_minimal(self):
        customer = make_customer()
        order = Order.objects.create(
            order_number="SM-20261101-0001",
            customer=customer,
            delivery_date="2026-11-15",
            delivery_address_snapshot=VALID_ADDRESS,
        )
        assert order.status == OrderStatus.PLACED
        assert order.currency == "SEK"
        assert str(order) == "SM-20261101-0001 [PLACED]"

    def test_order_number_unique(self):
        from django.db import IntegrityError, transaction
        customer = make_customer()
        Order.objects.create(
            order_number="SM-X", customer=customer,
            delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Order.objects.create(
                    order_number="SM-X", customer=customer,
                    delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
                )


@pytest.mark.django_db
class TestOrderLineModel:
    def test_line_total_auto_computed(self):
        customer = make_customer()
        product = make_product(price="89.00")
        order = Order.objects.create(
            order_number="SM-A", customer=customer,
            delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
        )
        line = OrderLine.objects.create(
            order=order,
            product=product,
            product_name_snapshot="Mercimek",
            quantity=3,
            unit_price_snapshot=Decimal("89.00"),
        )
        assert line.line_total == Decimal("267.00")