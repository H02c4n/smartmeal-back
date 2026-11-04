"""confirm_order servis testleri."""
from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.inventory.models import ReservationStatus, StockReservation
from apps.inventory.services.stock import get_available_balance
from apps.orders.models import OrderStatus
from apps.orders.services.fulfillment import cancel_order, confirm_order
from apps.orders.services.order import create_order

from .fixtures import (
    VALID_ADDRESS,
    make_approved_recipe,
    make_customer,
    make_product,
    make_released_lot,
)


def _place_order(customer, product, quantity=1):
    return create_order(
        customer=customer,
        delivery_date=timezone.now().date(),
        delivery_address=VALID_ADDRESS,
        items=[{"product_id": product.id, "quantity": quantity}],
    )


@pytest.mark.django_db
class TestConfirmOrder:
    def test_happy_path_single_lot(self):
        """Bir sipariş, bir line, bir ingredient, bir lot → CONFIRMED."""
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        # recipe_line: 500g un; order.quantity=2 → ihtiyaç 1000g
        ingredient = recipe.lines.first().ingredient
        lot = make_released_lot(ingredient=ingredient, qty=2000)

        order = _place_order(customer, product, quantity=2)
        assert order.status == OrderStatus.PLACED

        confirm_order(order_id=order.id)

        order.refresh_from_db()
        assert order.status == OrderStatus.CONFIRMED
        assert order.confirmed_at is not None

        # Rezervasyon lot'a bağlandı mı
        r = StockReservation.objects.get(order_id=order.id)
        assert r.lot_id == lot.id
        assert r.quantity == Decimal("1000.000")
        assert r.status == ReservationStatus.ACTIVE
        assert get_available_balance(lot) == Decimal("1000")

    def test_insufficient_stock_rolls_back(self):
        """Yetersiz stokta ValueError; sipariş PLACED'da kalır, rezervasyon yok."""
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ingredient = recipe.lines.first().ingredient
        make_released_lot(ingredient=ingredient, qty=500)  # ihtiyaç 1000, stok 500

        order = _place_order(customer, product, quantity=2)
        with pytest.raises(ValueError, match="Yetersiz stok"):
            confirm_order(order_id=order.id)

        order.refresh_from_db()
        assert order.status == OrderStatus.PLACED
        assert order.confirmed_at is None
        assert StockReservation.objects.filter(order_id=order.id).count() == 0

    def test_no_recipe_rolls_back(self):
        customer = make_customer()
        product = make_product()  # no approved recipe
        order = _place_order(customer, product, quantity=1)
        with pytest.raises(ValueError, match="onaylı reçete yok"):
            confirm_order(order_id=order.id)
        order.refresh_from_db()
        assert order.status == OrderStatus.PLACED

    def test_fefo_earliest_expiry_first(self):
        """FEFO: en erken son kullanma önce kullanılmalı."""
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ingredient = recipe.lines.first().ingredient
        # 300g erken expiry (2026-12-01), 300g geç (2027-06-01). İhtiyaç 400.
        early = make_released_lot(
            ingredient=ingredient, qty=300, expiry_date=date(2026, 12, 1)
        )
        late = make_released_lot(
            ingredient=ingredient, qty=300, expiry_date=date(2027, 6, 1)
        )

        order = _place_order(customer, product, quantity=1)  # 500g ihtiyaç
        confirm_order(order_id=order.id)

        # İlk 300 early'den, kalan 200 late'den rezerve
        reservations = {
            r.lot_id: r.quantity
            for r in StockReservation.objects.filter(order_id=order.id)
        }
        assert reservations[early.id] == Decimal("300.000")
        assert reservations[late.id] == Decimal("200.000")

    def test_fefo_null_expiry_last(self):
        """Son kullanma tarihi boş lot, tarihli lot'tan sonra gelir."""
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ingredient = recipe.lines.first().ingredient
        dated = make_released_lot(
            ingredient=ingredient, qty=300, expiry_date=date(2027, 1, 1)
        )
        no_expiry = make_released_lot(ingredient=ingredient, qty=300, expiry_date=None)

        order = _place_order(customer, product, quantity=1)  # 500g
        confirm_order(order_id=order.id)

        res = {r.lot_id: r.quantity for r in StockReservation.objects.filter(order_id=order.id)}
        # Önce dated (300), sonra no_expiry (200)
        assert res[dated.id] == Decimal("300.000")
        assert res[no_expiry.id] == Decimal("200.000")

    def test_multi_line_same_ingredient_aggregated(self):
        """İki farklı ürün aynı ingredient'i içeriyor → toplam ihtiyaç doğru."""
        customer = make_customer()
        p1 = make_product(sku="P1", name="Ürün 1")
        p2 = make_product(sku="P2", name="Ürün 2")
        r1 = make_approved_recipe(p1)
        r2 = make_approved_recipe(p2)
        # Her recipe 500g un; iki line × qty 1 → toplam 1000g
        ing = r1.lines.first().ingredient
        assert r2.lines.first().ingredient_id == ing.id
        make_released_lot(ingredient=ing, qty=1000)

        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[
                {"product_id": p1.id, "quantity": 1},
                {"product_id": p2.id, "quantity": 1},
            ],
        )
        confirm_order(order_id=order.id)
        r = StockReservation.objects.get(order_id=order.id)
        assert r.quantity == Decimal("1000.000")

    def test_yield_quantity_gt_one(self):
        """yield_quantity=2 → ihtiyaç yarıya iner."""
        customer = make_customer()
        product = make_product()
        # recipe: yield=2 adet, recipe_line=500g un → 1 porsiyon = 250g
        g = __import__(
            "apps.catalog.models", fromlist=["UnitOfMeasure"]
        ).UnitOfMeasure.objects.get_or_create(code="g", defaults={"name": "gram"})[0]
        adet = __import__(
            "apps.catalog.models", fromlist=["UnitOfMeasure"]
        ).UnitOfMeasure.objects.get_or_create(code="adet", defaults={"name": "adet"})[0]
        from apps.accounts.models import User
        from apps.catalog.models import Ingredient
        from apps.recipes.models import RecipeLine, RecipeVersion

        ing = Ingredient.objects.get_or_create(
            sku="ING-X", defaults={"name": "X", "base_unit": g}
        )[0]
        admin = User.objects.get_or_create(
            email="a@x.com", defaults={"is_staff": True, "is_superuser": True}
        )[0]
        recipe = RecipeVersion.objects.create(
            product=product, version_number=1,
            yield_quantity=Decimal("2"), yield_unit=adet,
        )
        RecipeLine.objects.create(
            recipe_version=recipe, ingredient=ing, quantity=Decimal("500"), unit=g
        )
        recipe.approve(admin)
        recipe.refresh_from_db()

        make_released_lot(ingredient=ing, qty=1000)
        order = _place_order(customer, product, quantity=1)
        confirm_order(order_id=order.id)
        r = StockReservation.objects.get(order_id=order.id)
        # 500g / 2 × 1 = 250g
        assert r.quantity == Decimal("250.000")

    def test_confirm_already_confirmed_fails(self):
        customer = make_customer()
        product = make_product()
        make_approved_recipe(product)
        ing = product.recipe_versions.first().lines.first().ingredient
        make_released_lot(ingredient=ing, qty=2000)
        order = _place_order(customer, product, quantity=1)
        confirm_order(order_id=order.id)
        with pytest.raises(ValueError, match="Yalnızca PLACED"):
            confirm_order(order_id=order.id)

    def test_confirm_cancelled_fails(self):
        customer = make_customer()
        product = make_product()
        order = _place_order(customer, product, quantity=1)
        cancel_order(order_id=order.id)
        with pytest.raises(ValueError, match="Yalnızca PLACED"):
            confirm_order(order_id=order.id)


@pytest.mark.django_db
class TestCancelOrder:
    def test_cancel_placed(self):
        customer = make_customer()
        product = make_product()
        order = _place_order(customer, product, quantity=1)
        cancelled = cancel_order(order_id=order.id, reason="test")
        assert cancelled.status == OrderStatus.CANCELLED
        assert cancelled.cancelled_at is not None
        assert cancelled.cancellation_reason == "test"

    def test_cancel_confirmed_releases_reservations(self):
        customer = make_customer()
        product = make_product()
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        lot = make_released_lot(ingredient=ing, qty=1000)

        order = _place_order(customer, product, quantity=1)
        confirm_order(order_id=order.id)
        assert get_available_balance(lot) == Decimal("500")

        cancel_order(order_id=order.id, reason="customer request")
        assert get_available_balance(lot) == Decimal("1000")
        r = StockReservation.objects.get(order_id=order.id)
        assert r.status == ReservationStatus.RELEASED

    def test_cancel_twice_fails(self):
        customer = make_customer()
        product = make_product()
        order = _place_order(customer, product, quantity=1)
        cancel_order(order_id=order.id)
        with pytest.raises(ValueError, match="İptal edilemez"):
            cancel_order(order_id=order.id)