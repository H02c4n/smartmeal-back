from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.common.pagination import (
    CreatedAtCursorPagination,
    OccurredAtCursorPagination,
)
from apps.inventory.models import InventoryLot, StockMovement

from .serializers import InventoryLotSerializer, StockMovementSerializer


class InventoryLotViewSet(ReadOnlyModelViewSet):
    serializer_class = InventoryLotSerializer
    permission_classes = [AllowAny]
    pagination_class = CreatedAtCursorPagination

    def get_queryset(self):
        qs = InventoryLot.objects.select_related("ingredient", "supplier")
        ingredient_id = self.request.query_params.get("ingredient")
        quality_status = self.request.query_params.get("quality_status")
        if ingredient_id:
            qs = qs.filter(ingredient_id=ingredient_id)
        if quality_status:
            qs = qs.filter(quality_status=quality_status)
        return qs


class StockMovementViewSet(ReadOnlyModelViewSet):
    serializer_class = StockMovementSerializer
    permission_classes = [AllowAny]
    pagination_class = OccurredAtCursorPagination

    def get_queryset(self):
        qs = StockMovement.objects.select_related("lot")
        lot_id = self.request.query_params.get("lot")
        movement_type = self.request.query_params.get("movement_type")
        if lot_id:
            qs = qs.filter(lot_id=lot_id)
        if movement_type:
            qs = qs.filter(movement_type=movement_type)
        return qs