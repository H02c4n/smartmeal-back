"""Ingredient testleri."""
import pytest

from apps.catalog.models import Ingredient, UnitOfMeasure


@pytest.mark.django_db
class TestIngredient:
    def test_create(self):
        g = UnitOfMeasure.objects.create(code="g", name="gram")
        ing = Ingredient.objects.create(sku="ING-UN", name="Un", base_unit=g)
        assert ing.sku == "ING-UN"
        assert ing.base_unit == g
        assert str(ing) == "ING-UN — Un"