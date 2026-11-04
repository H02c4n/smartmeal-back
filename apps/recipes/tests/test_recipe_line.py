"""RecipeLine testleri."""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.recipes.models import RecipeLine

from apps.recipes.tests.fixtures import make_ingredient, make_recipe, make_unit


@pytest.mark.django_db
class TestRecipeLine:
    def test_create_line(self):
        rv = make_recipe()
        ing = make_ingredient()
        unit = make_unit()
        line = RecipeLine.objects.create(
            recipe_version=rv, ingredient=ing, quantity=Decimal("500"), unit=unit
        )
        assert line.quantity == Decimal("500")
        assert line.waste_factor == Decimal("1.000")

    def test_duplicate_ingredient_per_version_fails(self):
        rv = make_recipe()
        ing = make_ingredient()
        unit = make_unit()
        RecipeLine.objects.create(
            recipe_version=rv, ingredient=ing, quantity=Decimal("100"), unit=unit
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                RecipeLine.objects.create(
                    recipe_version=rv, ingredient=ing, quantity=Decimal("200"), unit=unit
                )

    def test_add_line_to_approved_version_fails(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        rv = make_recipe()
        rv.approve(admin)
        rv.refresh_from_db()
        ing = make_ingredient()
        unit = make_unit()
        with pytest.raises(ValidationError):
            RecipeLine.objects.create(
                recipe_version=rv, ingredient=ing, quantity=Decimal("100"), unit=unit
            )

    def test_modify_line_of_approved_version_fails(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        rv = make_recipe()
        ing = make_ingredient()
        unit = make_unit()
        line = RecipeLine.objects.create(
            recipe_version=rv, ingredient=ing, quantity=Decimal("100"), unit=unit
        )
        rv.approve(admin)
        rv.refresh_from_db()
        line.quantity = Decimal("999")
        with pytest.raises(ValidationError):
            line.save()