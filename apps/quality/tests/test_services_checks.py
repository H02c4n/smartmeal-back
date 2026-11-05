"""record_check servisi testleri."""
from decimal import Decimal

import pytest

from apps.quality.models import QualityCheckResult, QualityCheckType
from apps.quality.services.checks import record_check

from apps.quality.tests.fixtures import make_batch


@pytest.mark.django_db
class TestRecordCheck:
    def test_record_pass(self):
        batch = make_batch()
        check = record_check(
            batch_id=batch.id,
            check_type=QualityCheckType.TEMPERATURE,
            result=QualityCheckResult.PASS,
            measurement_value=Decimal("4.5"),
            measurement_unit="°C",
        )
        assert check.result == QualityCheckResult.PASS
        assert check.batch_id == batch.id

    def test_record_for_lot(self):
        from apps.inventory.tests.fixtures import make_lot

        lot = make_lot()
        check = record_check(
            lot_id=lot.id,
            check_type=QualityCheckType.APPEARANCE,
            result=QualityCheckResult.PASS,
        )
        assert check.lot_id == lot.id

    def test_missing_target_rejected(self):
        with pytest.raises(ValueError, match="batch_id veya lot_id"):
            record_check(
                check_type=QualityCheckType.TEMPERATURE,
                result=QualityCheckResult.PASS,
            )

    def test_two_targets_rejected(self):
        from apps.inventory.tests.fixtures import make_lot

        batch = make_batch()
        lot = make_lot()
        with pytest.raises(ValueError, match="Sadece biri"):
            record_check(
                batch_id=batch.id,
                lot_id=lot.id,
                check_type=QualityCheckType.TEMPERATURE,
                result=QualityCheckResult.PASS,
            )

    def test_invalid_check_type_rejected(self):
        batch = make_batch()
        with pytest.raises(ValueError, match="check_type"):
            record_check(
                batch_id=batch.id,
                check_type="NOT_VALID",
                result=QualityCheckResult.PASS,
            )

    def test_invalid_result_rejected(self):
        batch = make_batch()
        with pytest.raises(ValueError, match="result"):
            record_check(
                batch_id=batch.id,
                check_type=QualityCheckType.TEMPERATURE,
                result="MAYBE",
            )

    def test_measurement_without_unit_rejected(self):
        batch = make_batch()
        with pytest.raises(ValueError, match="measurement_unit"):
            record_check(
                batch_id=batch.id,
                check_type=QualityCheckType.TEMPERATURE,
                result=QualityCheckResult.PASS,
                measurement_value=Decimal("4.5"),
                measurement_unit="",
            )