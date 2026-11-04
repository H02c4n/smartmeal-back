from rest_framework.routers import DefaultRouter

from .views import InventoryLotViewSet, StockMovementViewSet

router = DefaultRouter()
router.register("lots", InventoryLotViewSet, basename="inventory-lot")
router.register("movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = router.urls