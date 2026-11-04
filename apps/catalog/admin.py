from django.contrib import admin

from .models import Allergen, Ingredient, Product, ProductCategory, UnitOfMeasure


@admin.register(UnitOfMeasure)
class UnitOfMeasureAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "base_unit", "factor", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(Allergen)
class AllergenAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "name"]


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "base_unit", "is_active"]
    list_filter = ["is_active", "base_unit"]
    search_fields = ["sku", "name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["sku", "name", "category", "price", "currency", "is_active"]
    list_filter = ["is_active", "category", "currency"]
    search_fields = ["sku", "name"]
    filter_horizontal = ["allergens"]