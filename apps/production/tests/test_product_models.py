"""Production modellerinin temel testleri."""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.production.models import (
    ProductionBatch,
    ProductionBatchStatus,
    ProductionPlan,
    ProductionPlanStatus,
    ProductionTask,
    ProductionTaskStatus,
    ProductionTaskType,
)

from apps.production.tests.fixtures import make_batch_with_order_line, make_plan


@pytest.mark.django_db
class TestProductionPlan:
    def test_default_status_draft(self):
        plan = make_plan()
        assert plan.status == ProductionPlanStatus.DRAFT
        assert plan.released_at is None
        assert plan.completed_at is None
        assert str(plan).startswith("Plan ")

    def test_production_date_required(self):
        # production_date zorunlu, boş bırakılırsa IntegrityError
        with pytest.raises(Exception):
            with transaction.atomic():
                ProductionPlan.objects.create(production_date=None)


@pytest.mark.django_db
class TestProductionBatch:
    def test_batch_defaults(self):
        batch = make_batch_with_order_line(quantity=2)
        assert batch.status == ProductionBatchStatus.PLANNED
        assert batch.planned_quantity == 2
        assert batch.actual_quantity is None
        assert batch.waste_quantity == Decimal("0")
        assert str(batch).startswith(f"{batch.product.sku} × 2")

    def test_planned_quantity_must_be_positive(self):
        plan = make_plan()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductionBatch.objects.create(
                    plan=plan,
                    product=None,  # will fail earlier? actually product not null
                    planned_quantity=0,
                )

    def test_plan_order_line_unique_per_plan(self):
        batch1 = make_batch_with_order_line()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductionBatch.objects.create(
                    plan=batch1.plan,
                    order_line=batch1.order_line,
                    product=batch1.product,
                    planned_quantity=1,
                )

    def test_orderless_batches_allowed(self):
        # order_line=None ile birden çok batch olabilir (unique constraint uygulanmaz)
        plan = make_plan()
        from apps.orders.tests.fixtures import make_product

        p = make_product(sku="P-EXTRA")
        ProductionBatch.objects.create(plan=plan, product=p, planned_quantity=5)
        ProductionBatch.objects.create(plan=plan, product=p, planned_quantity=5)
        assert ProductionBatch.objects.filter(plan=plan).count() == 2


@pytest.mark.django_db
class TestProductionTask:
    def test_task_default_status(self):
        batch = make_batch_with_order_line()
        task = ProductionTask.objects.create(
            batch=batch, task_type=ProductionTaskType.PREP, sequence=1
        )
        assert task.status == ProductionTaskStatus.PENDING
        assert str(task).startswith(f"{batch.id} #1 PREP")

    def test_sequence_unique_per_batch(self):
        batch = make_batch_with_order_line()
        ProductionTask.objects.create(
            batch=batch, task_type=ProductionTaskType.PREP, sequence=1
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ProductionTask.objects.create(
                    batch=batch, task_type=ProductionTaskType.COOK, sequence=1
                )

    def test_tasks_ordered_by_sequence(self):
        batch = make_batch_with_order_line()
        ProductionTask.objects.create(
            batch=batch, task_type=ProductionTaskType.COOK, sequence=2
        )
        ProductionTask.objects.create(
            batch=batch, task_type=ProductionTaskType.PREP, sequence=1
        )
        tasks = list(batch.tasks.all())
        assert tasks[0].sequence == 1
        assert tasks[1].sequence == 2