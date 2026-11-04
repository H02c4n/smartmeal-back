"""Supplier testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.purchasing.models import Supplier


@pytest.mark.django_db
class TestSupplier:
    def test_create_minimal(self):
        s = Supplier.objects.create(name="Toptan Gıda A.Ş.")
        assert s.is_active is True
        assert str(s) == "Toptan Gıda A.Ş."

    def test_create_full(self):
        s = Supplier.objects.create(
            name="Yaş Sebze Ltd.",
            contact_person="Ahmet Y.",
            email="ahmet@yassebze.com",
            phone="+90 555 111 22 33",
        )
        assert s.contact_person == "Ahmet Y."
        assert s.email == "ahmet@yassebze.com"

    def test_name_unique(self):
        Supplier.objects.create(name="A")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Supplier.objects.create(name="A")

    def test_default_ordering_by_name(self):
        Supplier.objects.create(name="Zeta")
        Supplier.objects.create(name="Alpha")
        names = list(Supplier.objects.values_list("name", flat=True))
        assert names == ["Alpha", "Zeta"]