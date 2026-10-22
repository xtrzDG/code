"""
ElevenLabs Agents' phone numbers as rented numbers use them: the import of
a Twilio number with the account's credentials and the agent, assigning
another agent, removal (gone already is fine), and refusals as provider
errors with ElevenLabs' reason.
"""

import httpx
import pytest

from app.clients.elevenlabs.elevenlabs_phone_numbers_client import (
    ElevenLabsPhoneNumbersClient,
)
from app.schemas.dto.phone_numbers.provisioning import VoicePlatformImport
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.assistants.strings import VoiceAgentId
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.messaging.constrained_strings import TwilioAccountSid
from app.schemas.typings.platform.strings import PlatformSecret
from app.schemas.typings.telephony.constrained_strings import PhoneNumberLabel
from app.schemas.typings.telephony.strings import VoicePlatformPhoneNumberId
from tests.channels.recording_transport import RecordingTransport
from tests.contracts.contract_files import load_json_fixture

ACCOUNT = TwilioAccountSid("AC" + "0" * 32)
NUMBER_ID = VoicePlatformPhoneNumberId("phnum_0000000000000000000000000042")


def client(transport: RecordingTransport) -> ElevenLabsPhoneNumbersClient:
    return ElevenLabsPhoneNumbersClient(
        PlatformSecret("test-key-0000"),
        PublicBaseUrl("https://api.eu.residency.elevenlabs.io"),
        transport=transport.build(),
    )


def import_request(agent_id: str | None) -> VoicePlatformImport:
    return VoicePlatformImport(
        phone_number=E164PhoneNumber("+15125550142"),
        label=PhoneNumberLabel("Austin Coffee Lab"),
        agent_id=None if agent_id is None else VoiceAgentId(agent_id),
    )


@pytest.mark.parametrize("agent_id", ["agent_0000000000000000000000000007", None])
def test_a_twilio_number_is_imported_for_the_agent(agent_id: str | None) -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/v1/convai/phone-numbers$",
        load_json_fixture("elevenlabs", "phone_number_imported.json"),
    )

    number_id = client(transport).import_twilio_number(
        import_request(agent_id), ACCOUNT, PlatformSecret("test-token-0000")
    )

    assert number_id == NUMBER_ID
    [request] = transport.requests
    assert request.headers["xi-api-key"] == "test-key-0000"
    expected: dict[str, str] = {
        "provider": "twilio",
        "phone_number": "+15125550142",
        "label": "Austin Coffee Lab",
        "sid": str(ACCOUNT),
        "token": "test-token-0000",
    }
    if agent_id is not None:
        expected["agent_id"] = agent_id
    assert request.json() == expected


@pytest.mark.parametrize("agent_id", ["agent_0000000000000000000000000007", None])
def test_assigning_an_agent_patches_the_number(agent_id: str | None) -> None:
    transport = RecordingTransport()
    transport.respond(
        "PATCH", r"/v1/convai/phone-numbers/phnum_", {"phone_number_id": str(NUMBER_ID)}
    )

    client(transport).assign_agent(
        NUMBER_ID, None if agent_id is None else VoiceAgentId(agent_id)
    )

    [request] = transport.requests
    assert request.path == f"/v1/convai/phone-numbers/{NUMBER_ID}"
    assert request.json() == {"agent_id": agent_id}


@pytest.mark.parametrize("status_code", [200, 204, 404])
def test_removing_a_number_gone_already_is_fine(status_code: int) -> None:
    transport = RecordingTransport()
    transport.respond("DELETE", r"/v1/convai/phone-numbers/phnum_", {}, status_code)

    client(transport).delete_number(NUMBER_ID)

    assert [request.method for request in transport.requests] == ["DELETE"]


def test_a_refusal_names_the_reason() -> None:
    transport = RecordingTransport()
    transport.respond(
        "POST",
        r"/v1/convai/phone-numbers$",
        {
            "detail": {
                "status": "phone_number_already_exists",
                "message": "Phone number already exists",
            }
        },
        409,
    )

    with pytest.raises(
        ExternalServiceError, match="HTTP 409: Phone number already exists"
    ):
        client(transport).import_twilio_number(
            import_request(None), ACCOUNT, PlatformSecret("test-token-0000")
        )


def test_an_import_without_an_id_is_an_error() -> None:
    transport = RecordingTransport()
    transport.respond("POST", r"/v1/convai/phone-numbers$", {})

    with pytest.raises(ExternalServiceError, match="without its id"):
        client(transport).import_twilio_number(
            import_request(None), ACCOUNT, PlatformSecret("test-token-0000")
        )


def test_a_network_failure_is_a_provider_error() -> None:
    transport = RecordingTransport()
    transport.failure = httpx.ReadTimeout("slow")

    with pytest.raises(ExternalServiceError, match="ReadTimeout"):
        client(transport).delete_number(NUMBER_ID)
