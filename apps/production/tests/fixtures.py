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