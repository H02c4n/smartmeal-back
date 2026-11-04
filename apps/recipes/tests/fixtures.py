"""Test verisi yardımcıları."""
from decimal import Decimal

from apps.catalog.models import (
    Allergen,
    Ingredient,
    Product,
    ProductCategory,
    UnitOfMeasure,
)
from apps.recipes.models import RecipeLine, RecipeVersion


def make_unit(code="g", name="gram"):
    return UnitOfMeasure.objects.get_or_create(code=code, defaults={"name": name})[0]


def make_ingredient(sku="ING-UN", name="Un", unit=None):
    unit = unit or make_unit()
    return Ingredient.objects.create(sku=sku, name=name, base_unit=unit)


def make_product(sku="PRD-1", name="Test Ürün", category=None, price=Decimal("10.00")):
    if category is None:
        category = ProductCategory.objects.get_or_create(
            slug="corba", defaults={"name": "Çorba"}
        )[0]
    return Product.objects.create(
        sku=sku, name=name, category=category, price=price
    )


def make_recipe(product=None, version_number=1, status="DRAFT"):
    product = product or make_product()
    unit = make_unit("adet", "adet")
    return RecipeVersion.objects.create(
        product=product,
        version_number=version_number,
        yield_quantity=Decimal("1"),
        yield_unit=unit,
        status=status,
    )