"""
Yarın için üretim planı oluşturur. CONFIRMED siparişlerin her satırı
için bir batch yaratır (idempotent).

Kullanım:
  python manage.py plan_tomorrow
  python manage.py plan_tomorrow --date 2026-11-15
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from apps.production.services.planning import plan_batches_for_date


class Command(BaseCommand):
    help = "Belirtilen gün için üretim planı + batch'ler oluşturur."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="YYYY-MM-DD (varsayılan: yarın)",
            default=None,
        )

    def handle(self, *args, **options):
        if options["date"]:
            target = date.fromisoformat(options["date"])
        else:
            target = date.today() + timedelta(days=1)

        plan, created = plan_batches_for_date(production_date=target)
        self.stdout.write(
            self.style.SUCCESS(
                f"Plan {plan.id} ({plan.production_date}): {created} batch created."
            )
        )