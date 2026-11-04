from rest_framework import serializers

from apps.catalog.models import Ingredient, Product


class ProductSerializer(serializers.ModelSerializer):
    """Read-only product çıktısı. Müşteri web/mobil için."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    allergen_codes = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "description",
            "category",
            "category_name",
            "price",
            "currency",
            "allergen_codes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_allergen_codes(self, obj) -> list[str]:
        return list(obj.allergens.values_list("code", flat=True))


class IngredientSerializer(serializers.ModelSerializer):
    """Read-only ingredient çıktısı."""

    base_unit_code = serializers.CharField(source="base_unit.code", read_only=True)

    class Meta:
        model = Ingredient
        fields = [
            "id",
            "sku",
            "name",
            "base_unit",
            "base_unit_code",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields