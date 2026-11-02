"""The call settings of a brain world's business: recording on or off."""

from app.schemas.domain.call_settings import CallSettingsDocument
from app.schemas.typings.calls.booleans import IsCallRecordingEnabled
from app.utilities.calls.call_follow_up_keys import call_settings_id_of
from tests.brain.brain_world import BrainWorld


def record_calls(world: BrainWorld, is_recording_enabled: bool = True) -> None:
    """The owner switched call recording on (or explicitly off)."""

    now = world.clock.wall_clock().now_unix()
    world.call_settings_repo.save(
        CallSettingsDocument(
            id=call_settings_id_of(world.business.id),
            business_id=world.business.id,
            is_recording_enabled=IsCallRecordingEnabled(is_recording_enabled),
            created_at=now,
            updated_at=now,
        )
    )
