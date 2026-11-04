from django.contrib import admin, messages

from .models import Order, OrderLine, OrderStatus
from .services.fulfillment import cancel_order, confirm_order


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    fields = [
        "product",
        "product_name_snapshot",
        "quantity",
        "unit_price_snapshot",
        "line_total",
        "recipe_version_snapshot",
    ]
    readonly_fields = [
        "product_name_snapshot",
        "line_total",
        "recipe_version_snapshot",
    ]
    can_delete = False


@admin.action(description="Seçili PLACED siparişleri onayla (rezervasyonlu)")
def _action_confirm(modeladmin, request, queryset):
    for order in queryset.filter(status=OrderStatus.PLACED):
        try:
            confirm_order(order_id=order.id, actor=request.user)
        except ValueError as e:
            modeladmin.message_user(
                request, f"{order.order_number}: {e}", level=messages.ERROR
            )


@admin.action(description="Seçili siparişleri iptal et")
def _action_cancel(modeladmin, request, queryset):
    for order in queryset.filter(
        status__in=[OrderStatus.PLACED, OrderStatus.CONFIRMED]
    ):
        try:
            cancel_order(order_id=order.id, reason="admin cancel", actor=request.user)
        except ValueError as e:
            modeladmin.message_user(
                request, f"{order.order_number}: {e}", level=messages.ERROR
            )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "customer",
        "status",
        "delivery_date",
        "total_amount",
        "currency",
        "created_at",
    ]
    list_filter = ["status", "currency"]
    search_fields = ["order_number", "customer__email"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "order_number",
        "status",  # ★ state machine — sadece servis değiştirir
        "created_at",
        "updated_at",
        "confirmed_at",
        "cancelled_at",
        "subtotal",
        "total_amount",
        "delivery_address_snapshot",
    ]
    inlines = [OrderLineInline]
    actions = [_action_confirm, _action_cancel]
    fieldsets = (
        (None, {"fields": ("order_number", "customer", "status")}),
        ("Delivery", {"fields": ("delivery_date", "delivery_address_snapshot")}),
        (
            "Amounts",
            {"fields": ("currency", "subtotal", "tax_amount", "delivery_fee", "total_amount")},
        ),
        ("Notes", {"fields": ("notes", "cancellation_reason")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at", "confirmed_at", "cancelled_at")},
        ),
    )

    def has_add_permission(self, request):
        return False


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = [
        "order",
        "product_name_snapshot",
        "quantity",
        "unit_price_snapshot",
        "line_total",
    ]
    search_fields = ["order__order_number", "product_name_snapshot"]
    readonly_fields = ["line_total", "product_name_snapshot", "created_at"]