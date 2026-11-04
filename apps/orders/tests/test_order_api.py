"""Order API testleri."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient
from django.utils import timezone

from apps.accounts.models import User
from apps.inventory.models import ReservationStatus, StockReservation
from apps.orders.models import IdempotencyRecord, Order, OrderStatus

from .fixtures import (
    VALID_ADDRESS,
    make_approved_recipe,
    make_customer,
    make_product,
    make_released_lot,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer_client():
    user = User.objects.create_user(email="cust@example.com", password="pass12345")
    c = APIClient()
    c.force_authenticate(user=user)
    return c, user


@pytest.fixture
def staff_client():
    user = User.objects.create_user(
        email="staff@example.com", password="pass12345", is_staff=True
    )
    c = APIClient()
    c.force_authenticate(user=user)
    return c, user


def _order_payload(product, quantity=1):
    return {
        "delivery_date": str(timezone.now().date()),
        "delivery_address": VALID_ADDRESS,
        "items": [{"product_id": str(product.id), "quantity": quantity}],
    }


@pytest.mark.django_db
class TestOrderCreateAPI:
    def test_unauthenticated_401(self, api_client):
        p = make_product()
        res = api_client.post("/api/v1/orders/", _order_payload(p), format="json")
        assert res.status_code == 403

    def test_authenticated_create(self, customer_client):
        c, user = customer_client
        p = make_product(price="89.00")
        res = c.post("/api/v1/orders/", _order_payload(p, quantity=2), format="json")
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "PLACED"
        assert data["total_amount"] == "178.00"
        assert len(data["lines"]) == 1
        assert Order.objects.filter(customer=user).count() == 1

    def test_invalid_payload_400(self, customer_client):
        c, _ = customer_client
        res = c.post("/api/v1/orders/", {"items": []}, format="json")
        assert res.status_code == 400

    def test_idempotency_key_returns_same_response(self, customer_client):
        c, _ = customer_client
        p = make_product()
        payload = _order_payload(p)
        res1 = c.post("/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="k1")
        res2 = c.post("/api/v1/orders/", payload, format="json", HTTP_IDEMPOTENCY_KEY="k1")
        assert res1.status_code == res2.status_code == 201
        assert res1.json()["id"] == res2.json()["id"]
        assert Order.objects.count() == 1
        assert IdempotencyRecord.objects.count() == 1

    def test_idempotency_conflict_422(self, customer_client):
        c, _ = customer_client
        p1 = make_product(sku="P1")
        p2 = make_product(sku="P2")
        c.post("/api/v1/orders/", _order_payload(p1, 1), format="json", HTTP_IDEMPOTENCY_KEY="k1")
        res = c.post(
            "/api/v1/orders/", _order_payload(p2, 2), format="json", HTTP_IDEMPOTENCY_KEY="k1"
        )
        assert res.status_code == 422
        assert res.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.django_db
class TestOrderListAPI:
    def test_customer_sees_own_only(self, customer_client):
        c, user = customer_client
        other = make_customer("other@example.com")
        p = make_product()
        Order.objects.create(
            order_number="SM-A", customer=user,
            delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
        )
        Order.objects.create(
            order_number="SM-B", customer=other,
            delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
        )
        res = c.get("/api/v1/orders/")
        assert res.status_code == 200
        nums = [r["order_number"] for r in res.json()["results"]]
        assert "SM-A" in nums
        assert "SM-B" not in nums

    def test_staff_sees_all(self, staff_client):
        c, _ = staff_client
        a = make_customer("a@x.com")
        b = make_customer("b@x.com")
        Order.objects.create(order_number="SM-A", customer=a,
                             delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS)
        Order.objects.create(order_number="SM-B", customer=b,
                             delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS)
        res = c.get("/api/v1/orders/")
        assert len(res.json()["results"]) == 2


@pytest.mark.django_db
class TestOrderCancelConfirmAPI:
    def test_owner_cancel(self, customer_client):
        c, user = customer_client
        p = make_product()
        order = c.post("/api/v1/orders/", _order_payload(p), format="json").json()
        res = c.post(f"/api/v1/orders/{order['id']}/cancel/", {"reason": "test"}, format="json")
        assert res.status_code == 200
        assert res.json()["status"] == "CANCELLED"

    def test_other_user_cannot_cancel(self, customer_client):
        c, _ = customer_client
        other = make_customer("other2@x.com")
        o = Order.objects.create(
            order_number="SM-OTHER", customer=other,
            delivery_date="2026-11-15", delivery_address_snapshot=VALID_ADDRESS,
        )
        res = c.post(f"/api/v1/orders/{o.id}/cancel/", {}, format="json")
        assert res.status_code == 404  # get_queryset filter'ı yüzünden

    def test_owner_cannot_confirm(self, customer_client):
        c, _ = customer_client
        p = make_product()
        order = c.post("/api/v1/orders/", _order_payload(p), format="json").json()
        res = c.post(f"/api/v1/orders/{order['id']}/confirm/", {}, format="json")
        assert res.status_code == 403

    def test_staff_confirm_happy_path(self, staff_client):
        c, _ = staff_client
        # Başka müşterinin siparişini onaylıyor
        customer = make_customer("cust2@x.com")
        product = make_product()
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        make_released_lot(ingredient=ing, qty=2000)
        from apps.orders.services.order import create_order
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        res = c.post(f"/api/v1/orders/{order.id}/confirm/", {}, format="json")
        assert res.status_code == 200
        assert res.json()["status"] == "CONFIRMED"
        assert StockReservation.objects.filter(order_id=order.id, status=ReservationStatus.ACTIVE).exists()

    def test_staff_confirm_insufficient_stock_409(self, staff_client):
        c, _ = staff_client
        customer = make_customer("c3@x.com")
        product = make_product()
        recipe = make_approved_recipe(product)
        ing = recipe.lines.first().ingredient
        make_released_lot(ingredient=ing, qty=100)  # ihtiyaç 500
        from apps.orders.services.order import create_order
        order = create_order(
            customer=customer,
            delivery_date=timezone.now().date(),
            delivery_address=VALID_ADDRESS,
            items=[{"product_id": product.id, "quantity": 1}],
        )
        res = c.post(f"/api/v1/orders/{order.id}/confirm/", {}, format="json")
        assert res.status_code == 409
        assert res.json()["error"]["code"] == "INVALID_STATE_TRANSITION"