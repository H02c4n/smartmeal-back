"""QualityCheck model testleri."""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction

from apps.quality.models import QualityCheck, QualityCheckResult, QualityCheckType

from apps.quality.tests.fixtures import make_batch


@pytest.mark.django_db
class TestQualityCheck:
    def test_batch_check_pass(self):
        batch = make_batch()
        check = QualityCheck.objects.create(
            batch=batch,
            check_type=QualityCheckType.TEMPERATURE,
            result=QualityCheckResult.PASS,
            measurement_value=Decimal("4.5"),
            measurement_unit="°C",
        )
        assert check.result == QualityCheckResult.PASS
        assert "batch=" in str(check)

    def test_lot_check_fail(self):
        from apps.inventory.tests.fixtures import make_lot

        lot = make_lot()
        check = QualityCheck.objects.create(
            lot=lot,
            check_type=QualityCheckType.APPEARANCE,
            result=QualityCheckResult.FAIL,
        )
        assert check.result == QualityCheckResult.FAIL
        assert "lot=" in str(check)

    def test_both_batch_and_lot_rejected_by_clean(self):
        from apps.inventory.tests.fixtures import make_lot

        batch = make_batch()
        lot = make_lot()
        check = QualityCheck(
            batch=batch, lot=lot, check_type="TEMPERATURE", result="PASS"
        )
        with pytest.raises(Exception):
            check.full_clean()

    def test_neither_batch_nor_lot_rejected_by_clean(self):
        check = QualityCheck(check_type="TEMPERATURE", result="PASS")
        with pytest.raises(Exception):
            check.full_clean()

    def test_both_batch_and_lot_rejected_by_constraint(self):
        from apps.inventory.tests.fixtures import make_lot

        batch = make_batch()
        lot = make_lot()
        # DB constraint, save() bypasses clean()
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                QualityCheck.objects.create(
                    batch=batch, lot=lot, check_type="TEMPERATURE", result="PASS"
                )

    def test_measurement_without_unit_rejected(self):
        batch = make_batch()
        check = QualityCheck(
            batch=batch,
            check_type="TEMPERATURE",
            result="PASS",
            measurement_value=Decimal("4.5"),
            measurement_unit="",
        )
        with pytest.raises(Exception):
            check.full_clean()