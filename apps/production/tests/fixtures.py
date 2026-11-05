"""Production test yardımcıları."""
from django.utils import timezone

from apps.orders.tests.fixtures import (
    VALID_ADDRESS,
    make_approved_recipe,
    make_customer,
    make_product,
)
from apps.orders.services.order import create_order
from apps.production.models import ProductionBatch, ProductionPlan


def make_plan(production_date=None, site_id=None):
    return ProductionPlan.objects.create(
        production_date=production_date or timezone.now().date(),
        site_id=site_id,
    )


def make_batch_with_order_line(*, plan=None, quantity=1):
    """
    Bir sipariş oluşturur, ilk satırını alır ve plan altında batch yaratır.
    Batch üretim adımlarının test edilmesine hazır.
    """
    plan = plan or make_plan()
    customer = make_customer()
    product = make_product()
    recipe = make_approved_recipe(product)
    order = create_order(
        customer=customer,
        delivery_date=timezone.now().date(),
        delivery_address=VALID_ADDRESS,
        items=[{"product_id": product.id, "quantity": quantity}],
    )
    order_line = order.lines.first()
    batch = ProductionBatch.objects.create(
        plan=plan,
        order_line=order_line,
        product=product,
        recipe_version_snapshot=recipe,
        planned_quantity=quantity,
    )
    return batch


def make_completed_batch(*, qty=2, receipt=10000):
    """
    CONFIRMED sipariş + COMPLETED batch. Packing testleri için hazır.
    (Batch'in rezervasyonları `complete_batch` ile consume edilmiş olur.)
    """
    from datetime import timedelta

    from apps.inventory.services.stock import record_movement
    from apps.orders.services.fulfillment import confirm_order
    from apps.orders.services.order import create_order
    from apps.production.models import ProductionBatch
    from apps.production.services.execution import complete_batch, start_batch
    from apps.production.services.planning import plan_batches_for_date

    from apps.orders.tests.fixtures import (
        VALID_ADDRESS,
        make_approved_recipe,
        make_customer,
        make_product,
        make_released_lot,
    )

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

    start_batch(batch_id=batch.id)
    complete_batch(batch_id=batch.id, actual_quantity=qty)

    batch.refresh_from_db()
    return order, batch