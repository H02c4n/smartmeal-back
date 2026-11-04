"""RecipeVersion testleri."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User
from apps.recipes.models import RecipeVersion, RecipeVersionStatus

from apps.recipes.tests.fixtures import make_product, make_recipe


@pytest.mark.django_db
class TestRecipeVersion:
    def test_create_draft(self):
        rv = make_recipe(version_number=1)
        assert rv.status == RecipeVersionStatus.DRAFT
        assert rv.is_locked is False
        assert rv.approved_by is None

    def test_version_number_unique_per_product(self):
        product = make_product()
        make_recipe(product=product, version_number=1)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                make_recipe(product=product, version_number=1)

    def test_approve_sets_status_and_approver(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        rv = make_recipe()
        rv.approve(admin)
        rv.refresh_from_db()
        assert rv.status == RecipeVersionStatus.APPROVED
        assert rv.approved_by == admin
        assert rv.effective_from is not None
        assert rv.is_locked is True

    def test_approve_twice_fails(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        rv = make_recipe()
        rv.approve(admin)
        with pytest.raises(ValidationError):
            rv.approve(admin)

    def test_approved_version_cannot_be_modified(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        rv = make_recipe()
        rv.approve(admin)
        rv.refresh_from_db()
        rv.yield_quantity = 999
        with pytest.raises(ValidationError):
            rv.save()

    def test_new_version_can_be_created_after_approval(self):
        admin = User.objects.create_superuser(email="admin@x.com", password="x")
        product = make_product()
        v1 = make_recipe(product=product, version_number=1)
        v1.approve(admin)
        v2 = make_recipe(product=product, version_number=2)
        assert v2.status == RecipeVersionStatus.DRAFT
        assert v2.is_locked is False