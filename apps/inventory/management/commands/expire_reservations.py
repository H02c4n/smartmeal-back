from django.core.management.base import BaseCommand

from apps.inventory.services.reservation import expire_stale


class Command(BaseCommand):
    help = "Süresi geçmiş ACTIVE stok rezervasyonlarını EXPIRED'a çeker."

    def handle(self, *args, **options):
        count = expire_stale()
        self.stdout.write(self.style.SUCCESS(f"Expired {count} reservation(s)."))