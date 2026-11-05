from django.contrib import admin

from django.contrib import admin, messages
from django.utils import timezone

from apps.production.services.execution import (
    cancel_batch,
    complete_batch,
    start_batch,
)

from .models import (
    BatchIngredient,
    ProductionBatch,
    ProductionPlan,
    ProductionTask,
)


class ProductionBatchInline(admin.TabularInline):
    model = ProductionBatch
    extra = 0
    fields = [
        "product",
        "order_line",
        "planned_quantity",
        "actual_quantity",
        "status",
    ]
    readonly_fields = ["status"]
    autocomplete_fields = ["product", "order_line"]
    can_delete = False


@admin.register(ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ["production_date", "status", "site_id", "created_by", "created_at"]
    list_filter = ["status", "production_date"]
    date_hierarchy = "production_date"
    search_fields = ["notes"]
    readonly_fields = ["created_at", "updated_at", "released_at", "completed_at"]
    inlines = [ProductionBatchInline]
    fieldsets = (
        (None, {"fields": ("production_date", "site_id", "status")}),
        ("Meta", {"fields": ("created_by", "notes")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at", "released_at", "completed_at")},
        ),
    )


class BatchIngredientInline(admin.TabularInline):
    model = BatchIngredient
    extra = 0
    fields = ["lot", "planned_quantity", "actual_quantity", "unit"]
    readonly_fields = ["lot", "planned_quantity", "actual_quantity", "unit"]
    can_delete = False
    max_num = 0


class ProductionTaskInline(admin.TabularInline):
    model = ProductionTask
    extra = 0
    fields = ["sequence", "task_type", "status", "assigned_to"]
    readonly_fields = ["sequence", "task_type", "status", "assigned_to"]


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "plan",
        "planned_quantity",
        "actual_quantity",
        "status",
        "started_at",
        "completed_at",
    ]
    list_filter = ["status", "product"]
    search_fields = ["product__sku", "product__name", "order_line__order__order_number"]
    autocomplete_fields = ["product", "order_line", "recipe_version_snapshot", "plan"]
    readonly_fields = [
        "actual_quantity",
        "waste_quantity",
        "status",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
    ]
    inlines = [BatchIngredientInline, ProductionTaskInline]
    fieldsets = (
        (None, {"fields": ("plan", "product", "order_line", "recipe_version_snapshot")}),
        ("Quantities", {"fields": ("planned_quantity", "actual_quantity", "waste_quantity")}),
        ("Status", {"fields": ("status", "started_at", "completed_at")}),
        ("Notes", {"fields": ("notes",)}),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )

    actions = ["action_start", "action_complete", "action_cancel"]

    @admin.action(description="Seçili batch'leri başlat (PLANNED → IN_PROGRESS)")
    def action_start(self, request, queryset):
        for batch in queryset.filter(status="PLANNED"):
            try:
                start_batch(batch_id=batch.id, actor=request.user)
            except ValueError as e:
                self.message_user(
                    request, f"{batch.id}: {e}", level=messages.ERROR
                )

    @admin.action(description="Seçili batch'leri tamamla (IN_PROGRESS → COMPLETED)")
    def action_complete(self, request, queryset):
        for batch in queryset.filter(status="IN_PROGRESS"):
            try:
                complete_batch(
                    batch_id=batch.id,
                    actual_quantity=None,  # planned_quantity'yi kullan
                    actor=request.user,
                )
            except ValueError as e:
                self.message_user(
                    request, f"{batch.id}: {e}", level=messages.ERROR
                )

    @admin.action(description="Seçili batch'leri iptal et")
    def action_cancel(self, request, queryset):
        for batch in queryset.filter(status__in=["PLANNED", "IN_PROGRESS"]):
            try:
                cancel_batch(
                    batch_id=batch.id,
                    reason="admin cancel",
                    actor=request.user,
                )
            except ValueError as e:
                self.message_user(
                    request, f"{batch.id}: {e}", level=messages.ERROR
                )


@admin.register(BatchIngredient)
class BatchIngredientAdmin(admin.ModelAdmin):
    list_display = ["batch", "lot", "planned_quantity", "actual_quantity", "unit", "created_at"]
    search_fields = ["batch__product__sku", "lot__internal_lot_code"]
    readonly_fields = [
        "batch",
        "lot",
        "planned_quantity",
        "actual_quantity",
        "unit",
        "created_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProductionTask)
class ProductionTaskAdmin(admin.ModelAdmin):
    list_display = ["batch", "sequence", "task_type", "status", "assigned_to", "started_at"]
    list_filter = ["status", "task_type"]
    search_fields = ["batch__product__sku"]
    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]