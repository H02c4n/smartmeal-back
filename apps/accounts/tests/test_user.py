"""Custom User model testleri."""
import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import User


@pytest.mark.django_db
class TestUserModel:
    def test_create_user_with_email(self):
        user = User.objects.create_user(email="test@example.com", password="testpass123")
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("testpass123")
        assert str(user) == "test@example.com"

    def test_create_superuser(self):
        admin = User.objects.create_superuser(email="admin@example.com", password="adminpass123")
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_create_user_without_email_raises(self):
        with pytest.raises(ValueError, match="Email zorunludur"):
            User.objects.create_user(email="", password="x")

    def test_email_is_unique(self):
        User.objects.create_user(email="dup@example.com", password="x")
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(email="dup@example.com", password="y")

    def test_password_is_hashed(self):
        user = User.objects.create_user(email="hash@example.com", password="plaintext")
        assert user.password != "plaintext"
        assert user.check_password("plaintext")

    def test_email_domain_normalized(self):
        user = User.objects.create_user(email="Test@EXAMPLE.com", password="x")
        assert user.email == "Test@example.com"