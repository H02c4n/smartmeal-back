"""Product testleri."""
import pytest
from decimal import Decimal

from apps.catalog.models import Allergen, Product, ProductCategory


@pytest.mark.django_db
class TestProduct:
    def test_create_minimal(self):
        cat = ProductCategory.objects.create(name="Çorba", slug="corba")
        p = Product.objects.create(
            sku="PRD-MERCIMEK", name="Mercimek Çorbası", category=cat, price=Decimal("89.00")
        )
        assert p.currency == "SEK"
        assert str(p) == "PRD-MERCIMEK — Mercimek Çorbası"

    def test_with_allergens(self):
        cat = ProductCategory.objects.create(name="Çorba", slug="corba")
        gluten = Allergen.objects.create(code="gluten", name="Gluten")
        p = Product.objects.create(
            sku="P", name="Test", category=cat, price=Decimal("10.00")
        )
        p.allergens.add(gluten)
        assert list(p.allergens.all()) == [gluten]