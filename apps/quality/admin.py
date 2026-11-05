from django.contrib import admin

from .models import QualityCheck, QualityIncident


@admin.register(QualityCheck)
class QualityCheckAdmin(admin.ModelAdmin):
    list_display = [
        "checked_at",
        "check_type",
        "result",
        "target",
        "measurement_value",
        "measurement_unit",
        "checked_by",
    ]
    list_filter = ["check_type", "result"]
    search_fields = ["batch__product__sku", "lot__internal_lot_code", "notes"]
    date_hierarchy = "checked_at"
    autocomplete_fields = ["batch", "lot"]
    readonly_fields = ["checked_at"]

    @admin.display(description="Target")
    def target(self, obj):
        if obj.batch_id:
            return f"Batch {obj.batch.product.sku}"
        if obj.lot_id:
            return f"Lot {obj.lot.internal_lot_code}"
        return "—"


@admin.register(QualityIncident)
class QualityIncidentAdmin(admin.ModelAdmin):
    list_display = [
        "reported_at",
        "severity",
        "status",
        "target",
        "reported_by",
        "resolved_at",
    ]
    list_filter = ["severity", "status"]
    search_fields = ["batch__product__sku", "lot__internal_lot_code", "reason"]
    date_hierarchy = "reported_at"
    autocomplete_fields = ["batch", "lot"]
    readonly_fields = ["reported_at", "resolved_at", "resolved_by"]

    @admin.display(description="Target")
    def target(self, obj):
        if obj.batch_id:
            return f"Batch {obj.batch.product.sku}"
        if obj.lot_id:
            return f"Lot {obj.lot.internal_lot_code}"
        return "—"

    # Servis katmanından yönetilir; admin'de doğrudan düzenleme yok
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False