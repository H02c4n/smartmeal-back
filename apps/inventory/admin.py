from django.contrib import admin
from django.db.models import Sum

from .models import InventoryLot, StockMovement
from .services.stock import get_balance


@admin.register(InventoryLot)
class InventoryLotAdmin(admin.ModelAdmin):
    list_display = [
        "internal_lot_code",
        "ingredient",
        "supplier",
        "supplier_lot_code",
        "quality_status",
        "expiry_date",
        "balance",
    ]
    list_filter = ["quality_status", "supplier", "ingredient"]
    search_fields = [
        "internal_lot_code",
        "supplier_lot_code",
        "ingredient__sku",
        "ingredient__name",
    ]
    readonly_fields = ["created_at", "updated_at", "balance_display"]
    fieldsets = (
        (None, {"fields": ("internal_lot_code", "supplier_lot_code")}),
        ("Source", {"fields": ("ingredient", "supplier", "site_id")}),
        ("Dates & Quality", {"fields": ("received_at", "expiry_date", "quality_status")}),
        ("Computed", {"fields": ("balance_display",)}),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("ingredient", "supplier")

    @staticmethod
    def _format_decimal(value) -> str:
        """100.000 → '100', 100.500 → '100.5', 100.123 → '100.123'"""
        return format(value.normalize(), "f")

    @admin.display(description="Balance")
    def balance(self, obj):
        return self._format_decimal(get_balance(obj))

    @admin.display(description="Current balance (read-only)")
    def balance_display(self, obj):
        return self._format_decimal(get_balance(obj))


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = [
        "occurred_at",
        "lot",
        "movement_type",
        "quantity_delta",
        "reason",
        "actor",
    ]
    list_filter = ["movement_type"]
    search_fields = ["lot__internal_lot_code", "lot__ingredient__sku", "reason"]
    readonly_fields = ["occurred_at", "actor"]
    date_hierarchy = "occurred_at"

    # Append-only: admin'de düzenleme/silme yok
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False