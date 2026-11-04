"""Auth API testleri."""
import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestLoginLogoutMe:
    def test_login_success(self, api_client):
        User.objects.create_user(email="a@x.com", password="pass12345")
        res = api_client.post(
            "/api/v1/auth/login/", {"email": "a@x.com", "password": "pass12345"}, format="json"
        )
        assert res.status_code == 200
        assert res.json()["email"] == "a@x.com"

    def test_login_wrong_password(self, api_client):
        User.objects.create_user(email="a@x.com", password="pass12345")
        res = api_client.post(
            "/api/v1/auth/login/", {"email": "a@x.com", "password": "wrong"}, format="json"
        )
        assert res.status_code == 401

    def test_me_requires_login(self, api_client):
        res = api_client.get("/api/v1/me/")
        assert res.status_code == 403

    def test_me_returns_user(self, api_client):
        user = User.objects.create_user(email="a@x.com", password="pass12345")
        api_client.force_authenticate(user=user)
        res = api_client.get("/api/v1/me/")
        assert res.status_code == 200
        assert res.json()["email"] == "a@x.com"