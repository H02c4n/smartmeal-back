from django.contrib import admin

from .models import RecipeLine, RecipeVersion


class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 1
    fields = ["ingredient", "quantity", "unit", "waste_factor"]


@admin.register(RecipeVersion)
class RecipeVersionAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "version_number",
        "status",
        "yield_quantity",
        "yield_unit",
        "effective_from",
        "approved_by",
    ]
    list_filter = ["status", "yield_unit"]
    search_fields = ["product__sku", "product__name"]
    readonly_fields = ["approved_by", "effective_from", "created_at", "updated_at"]
    inlines = [RecipeLineInline]
    fieldsets = (
        (None, {"fields": ("product", "version_number", "status")}),
        ("Yield", {"fields": ("yield_quantity", "yield_unit")}),
        (
            "Approval",
            {"fields": ("approved_by", "effective_from", "effective_to")},
        ),
        ("Meta", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        # Admin'de status DRAFT → APPROVED yapıldıysa approve() metodunu kullan.
        if change:
            old = RecipeVersion.objects.get(pk=obj.pk)
            if (
                old.status == "DRAFT"
                and obj.status == "APPROVED"
            ):
                old.product = obj.product
                old.version_number = obj.version_number
                old.yield_quantity = obj.yield_quantity
                old.yield_unit = obj.yield_unit
                old.effective_to = obj.effective_to
                old.save()
                old.approve(request.user)
                obj.refresh_from_db()
                return
        super().save_model(request, obj, form, change)


@admin.register(RecipeLine)
class RecipeLineAdmin(admin.ModelAdmin):
    list_display = ["recipe_version", "ingredient", "quantity", "unit", "waste_factor"]
    list_filter = ["unit"]
    search_fields = ["ingredient__sku", "ingredient__name", "recipe_version__product__sku"]