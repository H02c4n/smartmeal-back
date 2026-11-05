"""Packing + delivery testleri için ortak fixture'lar."""
from apps.accounts.models import User
from apps.packing.models import Package, PackageStatus
from apps.packing.services.packing import (
    mark_ready_for_delivery,
    pack_order,
)
from apps.production.tests.fixtures import make_completed_batch


def make_ready_package(actor=None):
    """COMPLETED batch → READY_FOR_DELIVERY paket."""
    actor = actor or User.objects.filter(is_superuser=True).first()
    order, batch = make_completed_batch(qty=1)
    pkg = pack_order(order_id=order.id, actor=actor)
    pkg = mark_ready_for_delivery(package_id=pkg.id, actor=actor)
    return pkg, batch, order