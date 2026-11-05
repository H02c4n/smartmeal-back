"""Order testleri için ortak yardımcılar."""
from decimal import Decimal

from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Ingredient, Product, ProductCategory, UnitOfMeasure
from apps.recipes.models import RecipeLine, RecipeVersion, RecipeVersionStatus
from apps.inventory.models import InventoryLot, MovementType, QualityStatus
from apps.inventory.services.stock import record_movement
from apps.purchasing.models import Supplier

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
    product, _ = Product.objects.get_or_create(
        sku=sku,
        defaults={
            "name": name,
            "category": make_category(),
            "price": Decimal(price),
        },
    )
    return product

def make_approved_recipe(product, version=1):
    # Aynı product + versiyon zaten varsa dön
    existing = RecipeVersion.objects.filter(
        product=product, version_number=version
    ).first()
    if existing:
        return existing

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


def make_supplier(name="Test Supplier"):
    return Supplier.objects.get_or_create(name=name)[0]


def make_released_lot(*, ingredient, code=None, qty=None, expiry_date=None):
    """RELEASED lot yaratır; verilmişse `qty` kadar RECEIPT hareketi yazar."""
    import uuid
    from django.utils import timezone

    code = code or f"LOT-{uuid.uuid4().hex[:8]}"
    lot = InventoryLot.objects.create(
        ingredient=ingredient,
        supplier=make_supplier(),
        supplier_lot_code=code,
        internal_lot_code=code,
        received_at=timezone.now(),
        expiry_date=expiry_date,
        quality_status=QualityStatus.RELEASED,
    )
    if qty is not None:
        record_movement(
            lot_id=lot.id,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal(str(qty)),
        )
    return lot