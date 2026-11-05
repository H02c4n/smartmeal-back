from django.contrib import admin, messages

from .models import Package, PackageLine, PackageStatus
from .services.packing import cancel_package, mark_ready_for_delivery


class PackageLineInline(admin.TabularInline):
    model = PackageLine
    extra = 0
    fields = ["batch", "quantity", "created_at"]
    readonly_fields = ["batch", "quantity", "created_at"]
    can_delete = False
    max_num = 0


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = [
        "package_code",
        "order",
        "status",
        "packed_at",
        "packed_by",
        "created_at",
    ]
    list_filter = ["status"]
    search_fields = ["package_code", "order__order_number"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "package_code",
        "order",
        "status",
        "packed_by",
        "packed_at",
        "created_at",
        "updated_at",
    ]
    inlines = [PackageLineInline]
    actions = ["action_mark_ready", "action_cancel"]

    # Servis katmanından yönetilir; admin'de doğrudan ekleme yok
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Seçili paketleri READY_FOR_DELIVERY yap")
    def action_mark_ready(self, request, queryset):
        for pkg in queryset.filter(status=PackageStatus.PACKED):
            try:
                mark_ready_for_delivery(package_id=pkg.id, actor=request.user)
            except ValueError as e:
                self.message_user(request, f"{pkg.id}: {e}", level=messages.ERROR)

    @admin.action(description="Seçili paketleri iptal et")
    def action_cancel(self, request, queryset):
        for pkg in queryset.filter(
            status__in=[PackageStatus.PACKED, PackageStatus.READY_FOR_DELIVERY]
        ):
            try:
                cancel_package(
                    package_id=pkg.id, reason="admin cancel", actor=request.user
                )
            except ValueError as e:
                self.message_user(request, f"{pkg.id}: {e}", level=messages.ERROR)


@admin.register(PackageLine)
class PackageLineAdmin(admin.ModelAdmin):
    list_display = ["package", "batch", "quantity", "created_at"]
    search_fields = ["package__package_code", "batch__product__sku"]
    readonly_fields = ["package", "batch", "quantity", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False