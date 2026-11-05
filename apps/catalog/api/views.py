from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.catalog.models import Ingredient, Product
from apps.common.pagination import CreatedAtCursorPagination

from .serializers import IngredientSerializer, ProductSerializer


class ProductViewSet(ReadOnlyModelViewSet):
    """Salt-okunur ürün listesi. Anonymous erişime açık."""

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = CreatedAtCursorPagination

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("allergens")
        )


class IngredientViewSet(ReadOnlyModelViewSet):
    """Salt-okunur malzeme listesi. Anonymous erişime açık."""

    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = CreatedAtCursorPagination

    def get_queryset(self):
        return Ingredient.objects.filter(is_active=True).select_related("base_unit")