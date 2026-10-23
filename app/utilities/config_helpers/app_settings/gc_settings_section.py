"""
GC_FREEZE_AFTER_WARMUP and GC_THRESHOLDS: how the API and worker processes
keep garbage collection pauses out of the request path.
"""

from collections.abc import Mapping
from typing import TypedDict

from app.schemas.configurations.garbage_collection_settings import (
    GarbageCollectionSettings,
    GcThresholds,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.platform.constrained_integers import (
    GcFullCollectionThreshold,
    GcMiddleCollectionThreshold,
    GcYoungCollectionThreshold,
)
from app.utilities.config_helpers.app_settings.environment_variable_readers import (
    parse_setting,
    read_boolean,
    read_raw_list,
)

GC_THRESHOLDS_VARIABLE: str = "GC_THRESHOLDS"
# Young, middle and full: one number per generation of CPython's collector.
GC_THRESHOLD_COUNT: int = 3


class GarbageCollectionSettingsSection(TypedDict):
    """The `AppSettings` field of the garbage collector's tuning."""

    garbage_collection: GarbageCollectionSettings


def read_garbage_collection_settings(
    environment_variables: Mapping[str, str],
) -> GarbageCollectionSettingsSection:
    return GarbageCollectionSettingsSection(
        garbage_collection=GarbageCollectionSettings(
            is_freeze_after_warmup_enabled=read_boolean(
                environment_variables, "GC_FREEZE_AFTER_WARMUP", True
            ),
            thresholds=read_gc_thresholds(environment_variables),
        )
    )


def read_gc_thresholds(environment_variables: Mapping[str, str]) -> GcThresholds | None:
    """
    GC_THRESHOLDS: "young,middle,full" (e.g. "2000,10,10"); empty keeps
    Python's own thresholds.

    Raises:
        ValidationFailedError: not three integers, or one out of its range.
    """

    raw_values: list[str] = read_raw_list(environment_variables, GC_THRESHOLDS_VARIABLE)
    if not raw_values:
        return None

    if len(raw_values) != GC_THRESHOLD_COUNT or not all(
        raw_value.isdecimal() for raw_value in raw_values
    ):
        raise ValidationFailedError(
            f"{GC_THRESHOLDS_VARIABLE} must be three whole numbers "
            '"young,middle,full" (e.g. "2000,10,10"), or empty for '
            "Python's own thresholds."
        )

    young, middle, full = (int(raw_value) for raw_value in raw_values)
    return GcThresholds(
        young=parse_setting(GC_THRESHOLDS_VARIABLE, young, GcYoungCollectionThreshold),
        middle=parse_setting(
            GC_THRESHOLDS_VARIABLE, middle, GcMiddleCollectionThreshold
        ),
        full=parse_setting(GC_THRESHOLDS_VARIABLE, full, GcFullCollectionThreshold),
    )
