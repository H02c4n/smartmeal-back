"""
Sipariş servisleri. `create_order` dışında Order/OrderLine yaratmak
desteklenmez. Envanter entegrasyonu (rezervasyon) Faz 3 Adım 2'de
eklenecek; bu adımda yalnızca sipariş kaydı ve fiyat snapshot'ı.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Product
from apps.orders.models import Order, OrderLine, OrderStatus
from apps.recipes.models import RecipeVersion, RecipeVersionStatus

# Günlük sipariş numarası üreteci. Basit sıralı yaklaşım; yüksek
# eşzamanlılıkta retry mekanizmasıyla birlikte çalışır (bkz. aşağıda).
_MAX_ORDER_NUMBER_ATTEMPTS = 3


def _today_prefix() -> str:
    return f"SM-{timezone.now():%Y%m%d}-"


def _generate_order_number() -> str:
    """
    Bugünün siparişlerini sayıp son sıraya 1 ekler. Aynı milisaniyede iki
    transaction çalışırsa unique constraint çakışabilir — çağıran taraf
    retry yapar.
    """
    prefix = _today_prefix()
    last = (
        Order.objects.filter(order_number__startswith=prefix)
        .order_by("-order_number")
        .values_list("order_number", flat=True)
        .first()
    )
    if last:
        seq = int(last.rsplit("-", 1)[-1]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:04d}"


def _get_active_recipe_version(product: Product) -> RecipeVersion | None:
    """Ürünün o anki onaylı reçete sürümü (varsa)."""
    return (
        product.recipe_versions.filter(status=RecipeVersionStatus.APPROVED)
        .order_by("-version_number")
        .first()
    )


@transaction.atomic
def create_order(
    *,
    customer,
    delivery_date,
    delivery_address: dict,
    items: list[dict],
    notes: str = "",
) -> Order:
    """
    Sipariş oluşturur.

    `items`: [{"product_id": UUID, "quantity": int}, ...]
    Fiyatlar sunucuda ürün fiyatından okunur; istemciden gelen fiyat
    kabul edilmez.
    """
    if not items:
        raise ValueError("Sipariş en az bir satır içermelidir.")

    # Aynı ürün iki kez gönderilirse tek satırda birleştir
    seen: dict = {}
    for it in items:
        pid = it.get("product_id")
        qty = int(it.get("quantity", 0))
        if not pid or qty <= 0:
            raise ValueError(f"Geçersiz satır: {it}")
        seen[pid] = seen.get(pid, 0) + qty

    # Adres snapshot doğrulaması
    required_address_fields = {"street_address", "city", "postal_code", "country"}
    if not required_address_fields.issubset(set(delivery_address or {})):
        raise ValueError(
            f"Adres eksik. Zorunlu alanlar: {sorted(required_address_fields)}"
        )

    # Ürünleri tek sorguda çek
    products = {
        p.id: p
        for p in Product.objects.filter(id__in=list(seen.keys()), is_active=True)
    }
    if len(products) != len(seen):
        missing = [str(pid) for pid in seen if pid not in products]
        raise ValueError(f"Geçersiz veya pasif ürün(ler): {missing}")

    # Sipariş numarasını üret (retry'li)
    order = None
    for attempt in range(_MAX_ORDER_NUMBER_ATTEMPTS):
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    order_number=_generate_order_number(),
                    customer=customer,
                    status=OrderStatus.PLACED,
                    delivery_date=delivery_date,
                    delivery_address_snapshot=delivery_address,
                    currency="SEK",
                    notes=notes,
                )
            break
        except Exception:
            if attempt == _MAX_ORDER_NUMBER_ATTEMPTS - 1:
                raise

    # Satırlar ve toplamlar
    subtotal = Decimal("0")
    for pid, qty in seen.items():
        product = products[pid]
        recipe = _get_active_recipe_version(product)
        line = OrderLine.objects.create(
            order=order,
            product=product,
            product_name_snapshot=product.name,
            quantity=qty,
            unit_price_snapshot=product.price,
            recipe_version_snapshot=recipe,
        )
        subtotal += line.line_total

    order.subtotal = subtotal
    order.tax_amount = Decimal("0")   # Faz 4+'ta vergi politikası netleşince
    order.delivery_fee = Decimal("0")
    order.total_amount = subtotal + order.tax_amount + order.delivery_fee
    order.save(
        update_fields=["subtotal", "tax_amount", "delivery_fee", "total_amount", "updated_at"]
    )
    return order