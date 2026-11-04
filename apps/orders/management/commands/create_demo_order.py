"""
Demo sipariş oluşturur. Test/geliştirme için.

Kullanım:
  python manage.py create_demo_order
  python manage.py create_demo_order --email test@example.com --sku PRD-1 --qty 2
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Product
from apps.orders.services.order import create_order


class Command(BaseCommand):
    help = "Demo sipariş oluşturur (create_order servisi üzerinden)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="test@example.com")
        parser.add_argument("--sku", default=None)
        parser.add_argument("--qty", type=int, default=1)

    def handle(self, *args, **options):
        email = options["email"]
        sku = options["sku"]
        qty = options["qty"]

        try:
            customer = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(
                f"Kullanıcı bulunamadı: {email}. "
                f"Önce 'python manage.py createsuperuser' çalıştır veya "
                f"User.objects.create_user(...) ile yarat."
            )

        qs = Product.objects.filter(is_active=True)
        if sku:
            qs = qs.filter(sku=sku)
        product = qs.first()
        if not product:
            raise CommandError("Aktif ürün bulunamadı.")

        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address={
                "street_address": "Demo Street 1",
                "city": "Stockholm",
                "postal_code": "11122",
                "country": "SE",
            },
            items=[{"product_id": product.id, "quantity": qty}],
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {order.order_number} — {order.status} — "
                f"{order.total_amount} {order.currency}"
            )
        )