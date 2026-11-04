"""RoleAssignment model testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import RoleAssignment, RoleCode, User


@pytest.mark.django_db
class TestRoleAssignmentModel:
    def test_create_assignment(self):
        user = User.objects.create_user(email="u@example.com", password="x")
        ra = RoleAssignment.objects.create(user=user, role_code=RoleCode.CUSTOMER)
        assert ra.role_code == RoleCode.CUSTOMER
        assert ra.user == user
        assert str(ra) == f"{user.id} — CUSTOMER"

    def test_duplicate_role_for_same_user_raises(self):
        user = User.objects.create_user(email="u@example.com", password="x")
        RoleAssignment.objects.create(user=user, role_code=RoleCode.ADMIN)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                RoleAssignment.objects.create(user=user, role_code=RoleCode.ADMIN)

    def test_same_role_for_different_users_ok(self):
        u1 = User.objects.create_user(email="u1@example.com", password="x")
        u2 = User.objects.create_user(email="u2@example.com", password="y")
        RoleAssignment.objects.create(user=u1, role_code=RoleCode.ADMIN)
        RoleAssignment.objects.create(user=u2, role_code=RoleCode.ADMIN)
        assert RoleAssignment.objects.count() == 2

    def test_cascade_on_user_delete(self):
        user = User.objects.create_user(email="u@example.com", password="x")
        RoleAssignment.objects.create(user=user, role_code=RoleCode.ADMIN)
        assert RoleAssignment.objects.count() == 1
        user.delete()
        assert RoleAssignment.objects.count() == 0