from rest_framework.routers import DefaultRouter

from .views import IngredientViewSet, ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("ingredients", IngredientViewSet, basename="ingredient")

urlpatterns = router.urls