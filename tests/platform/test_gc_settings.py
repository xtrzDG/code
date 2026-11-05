"""GC_FREEZE_AFTER_WARMUP and GC_THRESHOLDS: defaults, values and refusals."""

import pytest

from app.schemas.configurations.garbage_collection_settings import GcThresholds
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)


def test_the_startup_heap_is_frozen_and_python_keeps_its_thresholds_by_default() -> (
    None
):
    settings = assemble_app_settings({}).garbage_collection

    assert settings.is_freeze_after_warmup_enabled is True
    assert settings.thresholds is None
    assert assemble_app_settings({"GC_THRESHOLDS": " "}).garbage_collection == settings


def test_the_freeze_can_be_turned_off_and_the_thresholds_set() -> None:
    settings = assemble_app_settings(
        {"GC_FREEZE_AFTER_WARMUP": "false", "GC_THRESHOLDS": "50000, 20, 100"}
    ).garbage_collection

    assert settings.is_freeze_after_warmup_enabled is False
    assert settings.thresholds == GcThresholds(
        young=GcYoungCollectionThreshold(50000),
        middle=GcMiddleCollectionThreshold(20),
        full=GcFullCollectionThreshold(100),
    )


@pytest.mark.parametrize(
    "environment",
    [
        {"GC_FREEZE_AFTER_WARMUP": "sometimes"},
        {"GC_THRESHOLDS": "2000,10"},
        {"GC_THRESHOLDS": "2000,10,10,10"},
        {"GC_THRESHOLDS": "2000,ten,10"},
        {"GC_THRESHOLDS": "2000,-10,10"},
        {"GC_THRESHOLDS": "2000.5,10,10"},
        # 0 would turn the collector off; below 100 it runs almost always.
        {"GC_THRESHOLDS": "0,10,10"},
        {"GC_THRESHOLDS": "99,10,10"},
        {"GC_THRESHOLDS": "2000,0,10"},
        {"GC_THRESHOLDS": "2000,10,0"},
        {"GC_THRESHOLDS": "20000000,10,10"},
        {"GC_THRESHOLDS": "2000,10,10001"},
    ],
)
def test_out_of_range_values_stop_the_start(environment: dict[str, str]) -> None:
    with pytest.raises(ValidationFailedError, match=next(iter(environment))):
        assemble_app_settings(environment)
