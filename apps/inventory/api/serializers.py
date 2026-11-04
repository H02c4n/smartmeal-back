from rest_framework import serializers

from apps.inventory.models import InventoryLot, StockMovement
from apps.inventory.services.stock import get_available_balance, get_balance


def _fmt(value) -> str:
    return format(value.normalize(), "f")


class InventoryLotSerializer(serializers.ModelSerializer):
    ingredient_sku = serializers.CharField(source="ingredient.sku", read_only=True)
    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    balance = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = InventoryLot
        fields = [
            "id",
            "internal_lot_code",
            "supplier_lot_code",
            "ingredient",
            "ingredient_sku",
            "ingredient_name",
            "supplier",
            "supplier_name",
            "expiry_date",
            "quality_status",
            "balance",
            "available_balance",
            "received_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_balance(self, obj) -> str:
        return _fmt(get_balance(obj))

    def get_available_balance(self, obj) -> str:
        return _fmt(get_available_balance(obj))


class StockMovementSerializer(serializers.ModelSerializer):
    lot_internal_code = serializers.CharField(
        source="lot.internal_lot_code", read_only=True
    )
    quantity_delta = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True
    )

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "lot",
            "lot_internal_code",
            "movement_type",
            "quantity_delta",
            "reason",
            "reference_type",
            "reference_id",
            "occurred_at",
        ]
        read_only_fields = fields