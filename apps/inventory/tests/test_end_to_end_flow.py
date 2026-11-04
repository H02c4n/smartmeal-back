"""
Faz 2 kapanışı: malzeme → reçete → lot → rezervasyon → tüketim
uçtan uca akışı. Her parça tek tek çalışıyordu; burada birlikte
çalıştıklarını kanıtlıyoruz.
"""
from decimal import Decimal

import pytest

from apps.accounts.models import User
from apps.catalog.models import (
    Allergen,
    Ingredient,
    Product,
    ProductCategory,
    UnitOfMeasure,
)
from apps.inventory.models import (
    InventoryLot,
    MovementType,
    QualityStatus,
    ReservationStatus,
)
from apps.inventory.services.reservation import consume, reserve
from apps.inventory.services.stock import (
    get_available_balance,
    get_balance,
    record_movement,
)
from apps.purchasing.models import Supplier
from apps.recipes.models import RecipeLine, RecipeVersion


@pytest.mark.django_db
class TestEndToEndFlow:
    def test_ingredient_to_consumption(self):
        # ---------- 1. Sözlükler ----------
        g = UnitOfMeasure.objects.create(code="g", name="gram")
        adet = UnitOfMeasure.objects.create(code="adet", name="adet")
        gluten = Allergen.objects.create(code="gluten", name="Gluten")

        # ---------- 2. Malzeme + Tedarikçi ----------
        un = Ingredient.objects.create(sku="ING-UN", name="Un", base_unit=g)
        supplier = Supplier.objects.create(name="Un Fabrikası A.Ş.")

        # ---------- 3. Kategori + Ürün ----------
        corba = ProductCategory.objects.create(name="Çorba", slug="corba")
        product = Product.objects.create(
            sku="PRD-MERCIMEK",
            name="Mercimek Çorbası",
            category=corba,
            price=Decimal("89.00"),
        )
        product.allergens.add(gluten)

        # ---------- 4. Reçete (draft) → approve ----------
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        recipe = RecipeVersion.objects.create(
            product=product,
            version_number=1,
            yield_quantity=Decimal("1"),
            yield_unit=adet,
        )
        RecipeLine.objects.create(
            recipe_version=recipe,
            ingredient=un,
            quantity=Decimal("500"),
            unit=g,
        )
        recipe.approve(admin)
        recipe.refresh_from_db()
        assert recipe.status == "APPROVED"
        assert recipe.is_locked is True
        assert recipe.lines.count() == 1

        # ---------- 5. Mal kabul: lot + RECEIPT ----------
        lot = InventoryLot.objects.create(
            ingredient=un,
            supplier=supplier,
            supplier_lot_code="UN-001",
            internal_lot_code="LOT-UN-001",
            quality_status=QualityStatus.RELEASED,
        )
        record_movement(
            lot_id=lot.id,
            movement_type=MovementType.RECEIPT,
            quantity=Decimal("1000"),
        )
        assert get_balance(lot) == Decimal("1000")
        assert get_available_balance(lot) == Decimal("1000")

        # ---------- 6. Rezervasyon: 500g ----------
        r = reserve(lot_id=lot.id, quantity=Decimal("500"))
        assert r.status == ReservationStatus.ACTIVE
        assert get_balance(lot) == Decimal("1000")           # fiziksel aynı
        assert get_available_balance(lot) == Decimal("500")  # 500 rezerve

        # ---------- 7. Tüketim ----------
        consume(reservation_id=r.id, actor=admin)
        r.refresh_from_db()
        assert r.status == ReservationStatus.CONSUMED
        assert get_balance(lot) == Decimal("500")
        assert get_available_balance(lot) == Decimal("500")

        # ---------- 8. Hareket defteri denetimi ----------
        movements = list(lot.movements.order_by("occurred_at"))
        assert len(movements) == 2
        assert movements[0].movement_type == MovementType.RECEIPT
        assert movements[0].quantity_delta == Decimal("1000")
        assert movements[1].movement_type == MovementType.CONSUMPTION
        assert movements[1].quantity_delta == Decimal("-500")
        assert movements[1].reference_type == "StockReservation"
        assert movements[1].reference_id == r.id

        # ---------- 9. Kalan 500g için ikinci rezervasyon ----------
        r2 = reserve(lot_id=lot.id, quantity=Decimal("500"))
        assert get_available_balance(lot) == Decimal("0")

        # ---------- 10. Aşırı rezervasyon engellenir ----------
        with pytest.raises(ValueError, match="Yetersiz"):
            reserve(lot_id=lot.id, quantity=Decimal("1"))

        # ---------- 11. Bırakınca geri döner ----------
        from apps.inventory.services.reservation import release
        release(reservation_id=r2.id)
        assert get_available_balance(lot) == Decimal("500")