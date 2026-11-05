"""Inventory API testleri."""
from decimal import Decimal

import pytest

from apps.inventory.models import MovementType, ReservationStatus
from apps.inventory.services.reservation import reserve
from apps.inventory.services.stock import record_movement

from apps.inventory.tests.fixtures import make_lot


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.mark.django_db
class TestInventoryLotAPI:
    def test_list_anonymous(self, api_client):
        lot = make_lot()
        res = api_client.get("/api/v1/inventory/lots")
        assert res.status_code == 200
        assert "results" in res.data

    def test_balance_and_available_in_response(self, api_client):
        lot = make_lot()
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("100"))
        reserve(lot_id=lot.id, quantity=Decimal("30"))
        res = api_client.get("/api/v1/inventory/lots")
        item = next(r for r in res.data["results"] if r["id"] == str(lot.id))
        assert item["balance"] == "100"
        assert item["available_balance"] == "70"


@pytest.mark.django_db
class TestStockMovementAPI:
    def test_list_and_filter(self, api_client):
        lot = make_lot()
        record_movement(lot_id=lot.id, movement_type=MovementType.RECEIPT, quantity=Decimal("50"))
        res = api_client.get("/api/v1/inventory/movements")
        assert res.status_code == 200
        assert len(res.data["results"]) == 1

        res2 = api_client.get(f"/api/v1/inventory/movements?lot={lot.id}")
        assert len(res2.data["results"]) == 1

        res3 = api_client.get(f"/api/v1/inventory/movements?movement_type=CONSUMPTION")
        assert len(res3.data["results"]) == 0