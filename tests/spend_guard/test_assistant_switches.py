"""
Kill switches (AI-10): an owner's pause holds every turn and call of the
business back like a hard limit; actions switched off by the owner or by a
SUPER platform admin are refused when a model asks for them, in chats and
on calls alike.
"""

import json

import pytest

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.contracts.use_case_contract import UseCaseContract
from app.repositories.assistant_settings_repository import (
    AssistantSettingsRepository,
)
from app.repositories.platform_safety_repositories import PlatformPauseRepository
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.spend import SpendLevel
from app.schemas.domain.assistant_settings import AssistantSettingsDocument
from app.schemas.domain.platform_pauses import PlatformPauseDocument
from app.schemas.dto.assistant_tools import (
    AssistantToolContext,
    AssistantToolInvocation,
    AssistantToolOutcome,
)
from app.schemas.dto.conversations import LlmToolCall, LlmToolResult
from app.schemas.dto.platform_pause import PlatformPauseCommand, PlatformPauseRequest
from app.schemas.dto.spend_guard import SpendCheckRequest
from app.schemas.exceptions.application_errors import (
    ConflictError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.conversations.strings import (
    LlmToolCallId,
    LlmToolInputJson,
    LlmToolResultJson,
)
from app.schemas.typings.localization.constrained_strings import (
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.spend.constrained_strings import PlatformPauseReason
from app.use_cases.conversations.tools.tool_switch_guard_use_case import (
    ToolSwitchGuardUseCase,
)
from tests.spend_guard.platform_pause_world import NOW, PauseWorld
from tests.spend_guard.spend_world import NOON, build_spend_world, micros

REASON: PlatformPauseReason = PlatformPauseReason("Bookings land on wrong days")


class RecordingTool(UseCaseContract[AssistantToolInvocation, AssistantToolOutcome]):
    def __init__(self) -> None:
        self.calls: list[AssistantToolName] = []

    def run(self, input_data: AssistantToolInvocation) -> AssistantToolOutcome:
        self.calls.append(input_data.call.tool_name)
        return AssistantToolOutcome(
            tool_name=input_data.call.tool_name,
            result=LlmToolResult(
                call_id=input_data.call.call_id,
                result_json=LlmToolResultJson('{"ok": true}'),
            ),
        )


def invocation(
    business_id: BusinessId, tool: AssistantToolName
) -> AssistantToolInvocation:
    return AssistantToolInvocation(
        context=AssistantToolContext(
            business_id=business_id,
            business_country_code=CountryCode("IT"),
            contact_id=ContactId(),
            conversation_id=ConversationId(),
            channel=ChannelKind.WHATSAPP,
            language=LanguageTag("it"),
            available_tools=list(AssistantToolName),
        ),
        call=LlmToolCall(
            call_id=LlmToolCallId("call_1"),
            tool_name=tool,
            input_json=LlmToolInputJson("{}"),
        ),
    )


def test_an_owners_pause_holds_the_business_like_a_hard_limit() -> None:
    world = build_spend_world()
    request = SpendCheckRequest(business=world.business, now=micros(NOON))

    def pause(is_paused: bool) -> None:
        def apply(settings: AssistantSettingsDocument) -> None:
            settings.is_paused = is_paused

        world.assistant_settings.change(world.business.id, apply, micros(NOON))

    pause(True)
    assert world.check.run(request).level is SpendLevel.HARD_LIMIT
    assert world.notifier.notifications == []
    assert world.audit_entries() == []
    pause(False)
    assert world.check.run(request).level is SpendLevel.NORMAL


def test_a_switched_off_tool_never_runs() -> None:
    business_id = BusinessId()
    settings = AssistantSettingsRepository(
        InMemoryDocumentCollectionAdapter(AssistantSettingsDocument)
    )
    pauses = PlatformPauseRepository(
        InMemoryDocumentCollectionAdapter(PlatformPauseDocument)
    )
    tool = RecordingTool()
    guard = ToolSwitchGuardUseCase(tool, settings, pauses)

    def switch_off(stored: AssistantSettingsDocument) -> None:
        stored.disabled_tools = [AssistantToolName.CREATE_BOOKING]

    settings.change(business_id, switch_off, NOW)
    refused = guard.run(invocation(business_id, AssistantToolName.CREATE_BOOKING))
    allowed = guard.run(invocation(business_id, AssistantToolName.CREATE_LEAD))

    assert refused.result.is_error is True
    assert (
        "create_booking is switched off"
        in json.loads(str(refused.result.result_json))["error"]
    )
    assert allowed.result.is_error is False
    assert tool.calls == [AssistantToolName.CREATE_LEAD]


def test_a_super_admin_switches_a_tool_off_for_every_business() -> None:
    world = PauseWorld()

    view = world.set_use_case().run(
        PlatformPauseCommand(
            user_id=world.super_admin,
            request=PlatformPauseRequest(
                is_paused=False,
                reason=REASON,
                disabled_tools=[AssistantToolName.SEND_PAYMENT_LINK],
            ),
        )
    )

    assert view.is_paused is False
    assert view.disabled_tools == [AssistantToolName.SEND_PAYMENT_LINK]
    [entry] = world.platform_entries()
    assert (entry.action, str(entry.entity_id)) == (
        AuditAction.UPDATE,
        "tools_switched",
    )
    tool = RecordingTool()
    guard = ToolSwitchGuardUseCase(
        tool,
        AssistantSettingsRepository(
            InMemoryDocumentCollectionAdapter(AssistantSettingsDocument)
        ),
        world.pauses,
    )
    refused = guard.run(invocation(BusinessId(), AssistantToolName.SEND_PAYMENT_LINK))
    assert refused.result.is_error is True
    assert tool.calls == []
    with pytest.raises(ConflictError):
        world.set_use_case().run(
            PlatformPauseCommand(
                user_id=world.super_admin,
                request=PlatformPauseRequest(is_paused=False, reason=REASON),
            )
        )


def test_the_platform_cannot_switch_off_the_handoff() -> None:
    world = PauseWorld()

    with pytest.raises(ValidationFailedError):
        world.set_use_case().run(
            PlatformPauseCommand(
                user_id=world.super_admin,
                request=PlatformPauseRequest(
                    is_paused=False,
                    reason=REASON,
                    disabled_tools=[AssistantToolName.HANDOFF_TO_HUMAN],
                ),
            )
        )
