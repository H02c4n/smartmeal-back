"""Catalog API endpoint testleri."""
from decimal import Decimal

import pytest

from apps.catalog.models import Allergen, Ingredient, Product, ProductCategory, UnitOfMeasure


def _make_product(sku="PRD-1", name="Test", active=True):
    cat = ProductCategory.objects.get_or_create(
        slug="corba", defaults={"name": "Çorba"}
    )[0]
    return Product.objects.create(
        sku=sku,
        name=name,
        category=cat,
        price=Decimal("89.00"),
        is_active=active,
    )


@pytest.mark.django_db
class TestProductAPI:
    def test_list_anonymous(self, api_client):
        _make_product()
        res = api_client.get("/api/v1/products")
        assert res.status_code == 200
        assert "results" in res.data
        assert len(res.data["results"]) == 1

    def test_detail(self, api_client):
        p = _make_product(sku="P-X", name="Mercimek")
        res = api_client.get(f"/api/v1/products/{p.id}")
        assert res.status_code == 200
        assert res.data["sku"] == "P-X"
        assert res.data["name"] == "Mercimek"
        assert res.data["price"] == "89.00"

    def test_inactive_product_excluded_from_list(self, api_client):
        active = _make_product(sku="P-A", name="Aktif", active=True)
        inactive = _make_product(sku="P-I", name="Pasif", active=False)
        res = api_client.get("/api/v1/products")
        ids = [r["id"] for r in res.data["results"]]
        assert str(active.id) in ids
        assert str(inactive.id) not in ids

    def test_inactive_product_detail_404(self, api_client):
        p = _make_product(active=False)
        res = api_client.get(f"/api/v1/products/{p.id}")
        assert res.status_code == 404

    def test_allergen_codes_included(self, api_client):
        p = _make_product()
        gluten = Allergen.objects.create(code="gluten", name="Gluten")
        p.allergens.add(gluten)
        res = api_client.get(f"/api/v1/products/{p.id}")
        assert res.data["allergen_codes"] == ["gluten"]

    def test_category_name_nested(self, api_client):
        p = _make_product()
        res = api_client.get(f"/api/v1/products/{p.id}")
        assert res.data["category_name"] == "Çorba"


@pytest.mark.django_db
class TestIngredientAPI:
    def test_list_anonymous(self, api_client):
        g = UnitOfMeasure.objects.create(code="g", name="gram")
        Ingredient.objects.create(sku="ING-UN", name="Un", base_unit=g)
        res = api_client.get("/api/v1/ingredients")
        assert res.status_code == 200
        assert len(res.data["results"]) == 1

    def test_detail(self, api_client):
        g = UnitOfMeasure.objects.create(code="g", name="gram")
        ing = Ingredient.objects.create(sku="ING-UN", name="Un", base_unit=g)
        res = api_client.get(f"/api/v1/ingredients/{ing.id}")
        assert res.status_code == 200
        assert res.data["sku"] == "ING-UN"
        assert res.data["base_unit_code"] == "g"

    def test_inactive_excluded(self, api_client):
        g = UnitOfMeasure.objects.create(code="g", name="gram")
        active = Ingredient.objects.create(sku="A", name="A", base_unit=g)
        inactive = Ingredient.objects.create(sku="I", name="I", base_unit=g, is_active=False)
        res = api_client.get("/api/v1/ingredients")
        ids = [r["id"] for r in res.data["results"]]
        assert str(active.id) in ids
        assert str(inactive.id) not in ids

    def test_pagination_structure(self, api_client):
        res = api_client.get("/api/v1/ingredients")
        assert res.status_code == 200
        assert "results" in res.data
        assert "next" in res.data
        assert "previous" in res.data