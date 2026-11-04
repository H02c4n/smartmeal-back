from rest_framework import serializers

from apps.orders.models import Order, OrderLine


class OrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = [
            "id",
            "product",
            "product_name_snapshot",
            "quantity",
            "unit_price_snapshot",
            "line_total",
            "recipe_version_snapshot",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    lines = OrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "delivery_date",
            "delivery_address_snapshot",
            "currency",
            "subtotal",
            "tax_amount",
            "delivery_fee",
            "total_amount",
            "notes",
            "cancellation_reason",
            "created_at",
            "confirmed_at",
            "cancelled_at",
            "lines",
        ]
        read_only_fields = fields


class OrderCreateItemSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    delivery_date = serializers.DateField()
    delivery_address = serializers.DictField()
    items = OrderCreateItemSerializer(many=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("En az bir satır zorunlu.")
        return value

    def validate_delivery_address(self, value):
        required = {"street_address", "city", "postal_code", "country"}
        missing = required - set(value.keys())
        if missing:
            raise serializers.ValidationError(f"Eksik adres alanları: {sorted(missing)}")
        return value