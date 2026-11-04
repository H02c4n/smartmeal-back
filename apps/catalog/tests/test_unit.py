"""UnitOfMeasure testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.catalog.models import UnitOfMeasure


@pytest.mark.django_db
class TestUnitOfMeasure:
    def test_create_base_unit(self):
        u = UnitOfMeasure.objects.create(code="g", name="gram")
        assert u.base_unit is None
        assert str(u) == "g (gram)"

    def test_create_derived_unit(self):
        base = UnitOfMeasure.objects.create(code="g", name="gram")
        kg = UnitOfMeasure.objects.create(
            code="kg", name="kilogram", base_unit=base, factor=1000
        )
        assert kg.base_unit == base
        assert kg.factor == 1000

    def test_code_is_unique(self):
        UnitOfMeasure.objects.create(code="g", name="gram")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UnitOfMeasure.objects.create(code="g", name="another gram")