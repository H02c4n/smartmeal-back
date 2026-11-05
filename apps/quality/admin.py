from django.contrib import admin, messages

from apps.quality.services.incidents import (
    close_incident,
    hold_incident,
    release_incident,
)

from .models import (
    QualityCheck,
    QualityIncident,
    QualityIncidentStatus,
)


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
    readonly_fields = ["checked_at", "checked_by"]

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
    readonly_fields = [
        "reported_at",
        "resolved_at",
        "resolved_by",
        "status",
        "reported_by",
    ]
    actions = ["action_hold", "action_release", "action_close"]

    @admin.display(description="Target")
    def target(self, obj):
        if obj.batch_id:
            return f"Batch {obj.batch.product.sku}"
        if obj.lot_id:
            return f"Lot {obj.lot.internal_lot_code}"
        return "—"

    # Alanlar readonly; state geçişleri sadece action'lardan
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Seçili incident'ları HOLD'a al (akışı bloklar)")
    def action_hold(self, request, queryset):
        for inc in queryset.filter(status=QualityIncidentStatus.OPEN):
            try:
                hold_incident(incident_id=inc.id, actor=request.user)
            except ValueError as e:
                self.message_user(request, f"{inc.id}: {e}", level=messages.ERROR)

    @admin.action(description="Seçili incident'ları RELEASE et (unblock)")
    def action_release(self, request, queryset):
        for inc in queryset.filter(status=QualityIncidentStatus.ON_HOLD):
            try:
                release_incident(
                    incident_id=inc.id, resolver=request.user, notes="admin release"
                )
            except ValueError as e:
                self.message_user(request, f"{inc.id}: {e}", level=messages.ERROR)

    @admin.action(description="Seçili incident'ları CLOSE et")
    def action_close(self, request, queryset):
        for inc in queryset.exclude(
            status__in=[
                QualityIncidentStatus.RELEASED,
                QualityIncidentStatus.CLOSED,
            ]
        ):
            try:
                close_incident(
                    incident_id=inc.id, resolver=request.user, notes="admin close"
                )
            except ValueError as e:
                self.message_user(request, f"{inc.id}: {e}", level=messages.ERROR)