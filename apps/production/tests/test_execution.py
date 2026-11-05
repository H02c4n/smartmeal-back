"""start_batch / complete_batch / cancel_batch servisleri testleri."""
from decimal import Decimal
from datetime import timedelta
import pytest
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockReservation
from apps.inventory.services.stock import get_balance
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
    BatchIngredient,
    ProductionBatch,
    ProductionBatchStatus,
    ProductionPlanStatus,
)
from apps.production.services.execution import (
    cancel_batch,
    complete_batch,
    start_batch,
)
from apps.production.services.planning import plan_batches_for_date


def _setup_confirmed_order_with_batch(*, qty=2, receipt=10000):
    target = timezone.now().date() + timedelta(days=1)
    customer = make_customer()
    product = make_product()
    recipe = make_approved_recipe(product)
    ing = recipe.lines.first().ingredient
    make_released_lot(ingredient=ing, qty=receipt)

    order = create_order(
        customer=customer,
        delivery_date=target,
        delivery_address=VALID_ADDRESS,
        items=[{"product_id": product.id, "quantity": qty}],
    )
    confirm_order(order_id=order.id)

    plan, _ = plan_batches_for_date(production_date=target)
    batch = ProductionBatch.objects.get(plan=plan)
    return batch, order, ing


@pytest.mark.django_db
class TestStartBatch:
    def test_start_planned(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        started = start_batch(batch_id=batch.id)
        assert started.status == ProductionBatchStatus.IN_PROGRESS
        assert started.started_at is not None

    def test_start_also_releases_plan(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        batch.plan.refresh_from_db()
        assert batch.plan.status == ProductionPlanStatus.IN_PROGRESS

    def test_start_twice_fails(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        with pytest.raises(ValueError, match="PLANNED"):
            start_batch(batch_id=batch.id)

    def test_start_completed_fails(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        complete_batch(batch_id=batch.id)
        with pytest.raises(ValueError, match="PLANNED"):
            start_batch(batch_id=batch.id)


@pytest.mark.django_db
class TestCompleteBatch:
    def test_complete_in_progress(self):
        batch, _, _ = _setup_confirmed_order_with_batch(qty=2)
        start_batch(batch_id=batch.id)
        completed = complete_batch(batch_id=batch.id, actual_quantity=2)
        assert completed.status == ProductionBatchStatus.COMPLETED
        assert completed.actual_quantity == 2
        assert completed.completed_at is not None

    def test_complete_without_start_fails(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        with pytest.raises(ValueError, match="IN_PROGRESS"):
            complete_batch(batch_id=batch.id)

    def test_complete_with_custom_quantity(self):
        batch, _, _ = _setup_confirmed_order_with_batch(qty=5)
        start_batch(batch_id=batch.id)
        completed = complete_batch(
            batch_id=batch.id,
            actual_quantity=4,
            waste_quantity=Decimal("1.5"),
        )
        assert completed.actual_quantity == 4
        assert completed.waste_quantity == Decimal("1.5")

    def test_complete_consumes_reservations_and_records_batch_ingredient(self):
        batch, order, ing = _setup_confirmed_order_with_batch(qty=2, receipt=10000)
        # qty=2 → reçete 500g/portion → 1000g rezerve
        lot = ing.lots.first()
        assert get_balance(lot) == Decimal("10000")

        start_batch(batch_id=batch.id)
        complete_batch(batch_id=batch.id, actual_quantity=2)

        # Reservation CONSUMED
        reservations = StockReservation.objects.filter(order_id=order.id)
        assert all(r.status == ReservationStatus.CONSUMED for r in reservations)

        # StockMovement yazıldı → balance düştü
        lot.refresh_from_db()
        assert get_balance(lot) == Decimal("9000")

        # BatchIngredient yazıldı (traceability)
        bi = BatchIngredient.objects.get(batch=batch, lot=lot)
        assert bi.actual_quantity == Decimal("1000.000")
        assert bi.unit == ing.base_unit

    def test_complete_updates_plan_status(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        complete_batch(batch_id=batch.id)
        batch.plan.refresh_from_db()
        assert batch.plan.status == ProductionPlanStatus.COMPLETED


@pytest.mark.django_db
class TestCancelBatch:
    def test_cancel_planned(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        cancelled = cancel_batch(batch_id=batch.id, reason="production error")
        assert cancelled.status == ProductionBatchStatus.CANCELLED

    def test_cancel_in_progress(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        cancelled = cancel_batch(batch_id=batch.id, reason="equipment failure")
        assert cancelled.status == ProductionBatchStatus.CANCELLED

    def test_cancel_completed_fails(self):
        batch, _, _ = _setup_confirmed_order_with_batch()
        start_batch(batch_id=batch.id)
        complete_batch(batch_id=batch.id)
        with pytest.raises(ValueError, match="PLANNED/IN_PROGRESS"):
            cancel_batch(batch_id=batch.id, reason="too late")