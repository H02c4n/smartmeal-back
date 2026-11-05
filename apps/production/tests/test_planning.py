"""plan_batches_for_date servisi testleri."""
from datetime import date, timedelta

import pytest
from django.utils import timezone

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
from apps.production.models import (
    ProductionBatch,
    ProductionPlan,
    ProductionPlanStatus,
)
from apps.production.services.planning import plan_batches_for_date


def _confirmed_order(*, delivery_date, qty=1):
    """Ürünün reçetesi + yeterli stok varsa CONFIRMED sipariş yaratır."""
    customer = make_customer()
    product = make_product()
    recipe = make_approved_recipe(product)
    ing = recipe.lines.first().ingredient
    make_released_lot(ingredient=ing, qty=10000)

    order = create_order(
        customer=customer,
        delivery_date=delivery_date,
        delivery_address=VALID_ADDRESS,
        items=[{"product_id": product.id, "quantity": qty}],
    )
    confirm_order(order_id=order.id)
    return order


@pytest.mark.django_db
class TestPlanBatchesForDate:
    def test_creates_plan_if_missing(self):
        target = timezone.now().date() + timedelta(days=1)
        _confirmed_order(delivery_date=target)
        plan, count = plan_batches_for_date(production_date=target)
        assert ProductionPlan.objects.filter(pk=plan.pk).exists()
        assert plan.status == ProductionPlanStatus.DRAFT
        assert count == 1

    def test_creates_one_batch_per_order_line(self):
        target = timezone.now().date() + timedelta(days=1)
        _confirmed_order(delivery_date=target, qty=3)
        plan, count = plan_batches_for_date(production_date=target)
        assert count == 1
        batch = ProductionBatch.objects.get(plan=plan)
        assert batch.planned_quantity == 3

    def test_idempotent_no_duplicates(self):
        target = timezone.now().date() + timedelta(days=1)
        _confirmed_order(delivery_date=target)
        plan1, count1 = plan_batches_for_date(production_date=target)
        plan2, count2 = plan_batches_for_date(production_date=target)
        assert plan1.pk == plan2.pk
        assert count1 == 1
        assert count2 == 0  # duplicate skipped
        assert ProductionBatch.objects.filter(plan=plan1).count() == 1

    def test_skips_placed_orders(self):
        target = timezone.now().date() + timedelta(days=1)
        customer = make_customer()
        product = make_product()
        # PLACED (not confirmed)
        create_order(
            customer=customer,
            delivery_date=target,
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        plan, count = plan_batches_for_date(production_date=target)
        assert count == 0

    def test_skips_other_delivery_dates(self):
        target = timezone.now().date() + timedelta(days=1)
        other_date = target + timedelta(days=5)
        _confirmed_order(delivery_date=other_date)
        plan, count = plan_batches_for_date(production_date=target)
        assert count == 0