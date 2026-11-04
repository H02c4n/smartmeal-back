from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.catalog.models import Ingredient, Product

from .pagination import StandardCursorPagination
from .serializers import IngredientSerializer, ProductSerializer


class ProductViewSet(ReadOnlyModelViewSet):
    """
    Salt-okunur ürün listesi. Anonymous erişime açık (müşteri menüsü).
    Yalnızca is_active=True ürünler listelenir.
    """

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardCursorPagination

    def get_queryset(self):
        return (
            Product.objects.filter(is_active=True)
            .select_related("category")
            .prefetch_related("allergens")
        )


class IngredientViewSet(ReadOnlyModelViewSet):
    """
    Salt-okunur malzeme listesi. Anonymous erişime açık.
    Yalnızca is_active=True malzemeler listelenir.
    """

    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardCursorPagination

    def get_queryset(self):
        return (
            Ingredient.objects.filter(is_active=True).select_related("base_unit")
        )