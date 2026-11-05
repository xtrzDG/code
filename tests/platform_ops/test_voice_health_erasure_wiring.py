"""voice_health counts the ElevenLabs calls of erasure like every other call."""

import pytest

from app.adapters.monitoring.bucket_signal_counter_adapter import (
    BucketSignalCounterAdapter,
)
from app.containers.app import AppContainer
from app.schemas.constants.monitoring import PlatformSignal
from app.schemas.constants.privacy import ProcessorErasureReason, SubProcessor
from app.schemas.dto.processor_erasure import ProcessorErasureScope
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ProviderCallId
from app.utilities.config_helpers.app_settings.app_settings_assembler import (
    assemble_app_settings,
)
from tests.e2e.workshop_container import replace_provider
from tests.platform_ops.elevenlabs_fakes import ScriptedElevenLabsClient


def test_a_failed_erasure_at_elevenlabs_counts_as_a_voice_api_error() -> None:
    container = AppContainer()
    replace_provider(
        container.config.app_settings,
        assemble_app_settings({"ELEVENLABS_API_KEY": "test-token-0000"}),
    )
    replace_provider(
        container.clients.elevenlabs_client,
        ScriptedElevenLabsClient([ExternalServiceError("ElevenLabs said 503.")]),
    )
    erasure = container.facilitators.processor_erasure()
    scope = ProcessorErasureScope(
        business_id=BusinessId(),
        reason=ProcessorErasureReason.CONTACT_ERASURE,
        provider_call_ids=[ProviderCallId("conv_1")],
    )

    with pytest.raises(ExternalServiceError):
        erasure.erase(SubProcessor.ELEVENLABS, scope)

    wall_clock = container.time_provider.microsecond_wall_clock()
    signals = BucketSignalCounterAdapter(
        buckets=container.adapters.rate_limit_buckets(), wall_clock=wall_clock
    )
    now = wall_clock.now_unix()
    calls = signals.read(PlatformSignal.VOICE_API_CALL, now)
    errors = signals.read(PlatformSignal.VOICE_API_ERROR, now)
    assert (int(calls.current), int(errors.current)) == (1, 1)
