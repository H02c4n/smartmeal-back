from django.contrib import admin, messages

from .models import DeliveryRun, DeliveryStop, DeliveryRunStatus
from .services.delivery import (
    cancel_run,
    complete_stop,
    fail_stop,
    start_run,
)


class DeliveryStopInline(admin.TabularInline):
    model = DeliveryStop
    extra = 0
    fields = ["sequence", "package", "status", "delivered_at", "failure_reason"]
    readonly_fields = ["sequence", "package", "status", "delivered_at", "failure_reason"]
    can_delete = False
    max_num = 0


@admin.register(DeliveryRun)
class DeliveryRunAdmin(admin.ModelAdmin):
    list_display = [
        "delivery_date",
        "driver",
        "status",
        "stop_count",
        "started_at",
        "completed_at",
    ]
    list_filter = ["status", "delivery_date"]
    date_hierarchy = "delivery_date"
    search_fields = ["driver__email"]
    readonly_fields = ["status", "started_at", "completed_at", "created_at", "updated_at"]
    inlines = [DeliveryStopInline]
    actions = ["action_start", "action_cancel"]

    @admin.display(description="Stops")
    def stop_count(self, obj):
        return obj.stops.count()

    @admin.action(description="Seçili run'ları başlat")
    def action_start(self, request, queryset):
        for run in queryset.filter(status=DeliveryRunStatus.PLANNED):
            try:
                start_run(run_id=run.id, actor=request.user)
            except ValueError as e:
                self.message_user(request, f"{run.id}: {e}", level=messages.ERROR)

    @admin.action(description="Seçili run'ları iptal et")
    def action_cancel(self, request, queryset):
        for run in queryset.exclude(
            status__in=[DeliveryRunStatus.COMPLETED, DeliveryRunStatus.CANCELLED]
        ):
            try:
                cancel_run(run_id=run.id, reason="admin cancel", actor=request.user)
            except ValueError as e:
                self.message_user(request, f"{run.id}: {e}", level=messages.ERROR)


@admin.register(DeliveryStop)
class DeliveryStopAdmin(admin.ModelAdmin):
    list_display = [
        "run",
        "sequence",
        "package",
        "status",
        "delivered_at",
        "failure_reason",
    ]
    list_filter = ["status"]
    search_fields = ["package__package_code", "run__driver__email"]
    readonly_fields = [
        "run",
        "package",
        "sequence",
        "status",
        "delivered_at",
        "failure_reason",
        "proof_reference",
        "created_at",
        "updated_at",
    ]
    actions = ["action_deliver", "action_fail"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Seçili durakları 'Delivered' işaretle")
    def action_deliver(self, request, queryset):
        for stop in queryset.filter(status="PENDING"):
            try:
                complete_stop(
                    stop_id=stop.id, proof_reference="admin", actor=request.user
                )
            except ValueError as e:
                self.message_user(request, f"{stop.id}: {e}", level=messages.ERROR)

    @admin.action(description="Seçili durakları 'Failed' işaretle")
    def action_fail(self, request, queryset):
        for stop in queryset.filter(status="PENDING"):
            try:
                fail_stop(
                    stop_id=stop.id, reason="admin marked failed", actor=request.user
                )
            except ValueError as e:
                self.message_user(request, f"{stop.id}: {e}", level=messages.ERROR)