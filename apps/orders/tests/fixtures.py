"""Order testleri için ortak yardımcılar."""
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Ingredient, Product, ProductCategory, UnitOfMeasure
from apps.recipes.models import RecipeLine, RecipeVersion, RecipeVersionStatus


VALID_ADDRESS = {
    "street_address": "Testgatan 1",
    "city": "Stockholm",
    "postal_code": "11122",
    "country": "SE",
}


def make_customer(email="cust@example.com"):
    return User.objects.get_or_create(email=email, defaults={"password": "x"})[0]


def make_category():
    return ProductCategory.objects.get_or_create(
        slug="corba", defaults={"name": "Çorba"}
    )[0]


def make_product(sku="PRD-1", name="Mercimek Çorbası", price="89.00"):
    return Product.objects.create(
        sku=sku,
        name=name,
        category=make_category(),
        price=Decimal(price),
    )


def make_approved_recipe(product, version=1):
    g = UnitOfMeasure.objects.get_or_create(code="g", defaults={"name": "gram"})[0]
    adet = UnitOfMeasure.objects.get_or_create(code="adet", defaults={"name": "adet"})[0]
    ing = Ingredient.objects.get_or_create(
        sku="ING-UN", defaults={"name": "Un", "base_unit": g}
    )[0]
    admin = User.objects.get_or_create(
        email="admin@x.com", defaults={"is_staff": True, "is_superuser": True}
    )[0]
    recipe = RecipeVersion.objects.create(
        product=product,
        version_number=version,
        yield_quantity=Decimal("1"),
        yield_unit=adet,
    )
    RecipeLine.objects.create(
        recipe_version=recipe, ingredient=ing, quantity=Decimal("500"), unit=g
    )
    recipe.approve(admin)
    recipe.refresh_from_db()
    assert recipe.status == RecipeVersionStatus.APPROVED
    return recipe