"""
Üretim planlama servisi. Siparişlerden batch yaratır.
"""
from django.db import transaction
from django.utils import timezone

from apps.orders.models import Order, OrderStatus
from apps.production.models import (
    ProductionBatch,
    ProductionPlan,
    ProductionPlanStatus,
)


@transaction.atomic
def plan_batches_for_date(
    production_date,
    site_id=None,
    actor=None,
) -> tuple[ProductionPlan, int]:
    """
    Belirtilen gün için CONFIRMED siparişlerden batch üretir.

    - Plan yoksa yaratır (DRAFT)
    - Her CONFIRMED siparişin her line'ı için bir batch yaratır
    - Idempotent: (plan, order_line) varsa atlar

    Returns:
        (plan, created_count)
    """
    plan, _ = ProductionPlan.objects.get_or_create(
        production_date=production_date,
        site_id=site_id,
        defaults={"created_by": actor} if actor else {},
    )

    orders = (
        Order.objects.filter(
            status=OrderStatus.CONFIRMED,
            delivery_date=production_date,
        )
        .prefetch_related("lines")
    )

    created_count = 0
    for order in orders:
        for line in order.lines.all():
            if ProductionBatch.objects.filter(plan=plan, order_line=line).exists():
                continue
            ProductionBatch.objects.create(
                plan=plan,
                order_line=line,
                product=line.product,
                recipe_version_snapshot=line.recipe_version_snapshot,
                planned_quantity=line.quantity,
            )
            created_count += 1

    return plan, created_count