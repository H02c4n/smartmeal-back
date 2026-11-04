from django.contrib import admin

from .models import Order, OrderLine


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
        "created_at",
        "updated_at",
        "confirmed_at",
        "cancelled_at",
        "subtotal",
        "total_amount",
        "delivery_address_snapshot",
    ]
    inlines = [OrderLineInline]
    fieldsets = (
        (None, {"fields": ("order_number", "customer", "status")}),
        ("Delivery", {"fields": ("delivery_date", "delivery_address_snapshot")}),
        ("Amounts", {"fields": ("currency", "subtotal", "tax_amount", "delivery_fee", "total_amount")}),
        ("Notes", {"fields": ("notes", "cancellation_reason")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "confirmed_at", "cancelled_at")}),
    )

    # Sipariş servis katmanından yönetilir
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