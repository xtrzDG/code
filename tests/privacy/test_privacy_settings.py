"""
Settings → Privacy: the owner's retention periods (defaults until
changed), a shorter period asks for a recent sign-in, every change is
audited, staff are refused, and the hosted chat's privacy notice reads
the periods the business chose.
"""

from dataclasses import dataclass, field

import pytest
from typed_time_provider import Microseconds

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.repositories.retention_settings_repositories import (
    BusinessPrivacySettingsRepository,
    RetentionPurgeStateRepository,
)
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.privacy import SubProcessor
from app.schemas.domain.business_privacy_settings import (
    BusinessPrivacySettingsDocument,
)
from app.schemas.domain.retention_purges import (
    RetentionPurgeCounts,
    RetentionPurgeStateDocument,
)
from app.schemas.dto.retention import (
    PrivacySettingsQuery,
    PrivacySettingsRequest,
    UpdatePrivacySettingsCommand,
)
from app.schemas.exceptions.application_errors import AccessDeniedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.compliance.constrained_integers import ErasedRecordCount
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.privacy.constrained_integers import (
    ConversationRetentionDays,
    LlmTurnRetentionDays,
)
from app.use_cases.compliance.privacy_settings.get_privacy_settings_use_case import (
    GetPrivacySettingsUseCase,
)
from app.use_cases.compliance.privacy_settings.update_privacy_settings_use_case import (
    UpdatePrivacySettingsUseCase,
)
from tests.compliance.business_with_staff import business_with_staff
from tests.privacy.processor_erasure_doubles import ProcessorErasureBed
from tests.users.accounts_testbed import AccountsTestbed, build_accounts_testbed


@dataclass
class ToggleStepUp:
    """A step-up guard that refuses while `is_required` (and counts checks)."""

    is_required: bool = False
    checks: list[bool] = field(default_factory=list[bool])

    def require_recent_authentication(self) -> None:
        self.checks.append(self.is_required)
        if self.is_required:
            raise StepUpRequiredError("Confirm it is you.")


@dataclass
class PrivacyBed:
    testbed: AccountsTestbed = field(default_factory=build_accounts_testbed)
    step_up: ToggleStepUp = field(default_factory=ToggleStepUp)

    def __post_init__(self) -> None:
        self.settings = BusinessPrivacySettingsRepository(
            InMemoryDocumentCollectionAdapter(BusinessPrivacySettingsDocument)
        )
        self.states = RetentionPurgeStateRepository(
            InMemoryDocumentCollectionAdapter(RetentionPurgeStateDocument)
        )
        erasure = ProcessorErasureBed().facilitator()
        self.get = GetPrivacySettingsUseCase(
            authorize_business_access=self.testbed.authorize_business_access,
            privacy_settings_repo=self.settings,
            purge_state_repo=self.states,
            processor_erasure=erasure,
        )
        self.update = UpdatePrivacySettingsUseCase(
            authorize_business_access=self.testbed.authorize_business_access,
            privacy_settings_repo=self.settings,
            purge_state_repo=self.states,
            processor_erasure=erasure,
            audit_log_repo=self.testbed.audit_log_repo,
            step_up=self.step_up,
            wall_clock=self.testbed.clock.build_wall_clock(),
        )
        self.owner_id, self.staff_id, self.business = business_with_staff(self.testbed)

    def change(self, conversations: int, model_records: int) -> None:
        self.update.run(
            UpdatePrivacySettingsCommand(
                user_id=self.owner_id,
                business_id=self.business.id,
                request=PrivacySettingsRequest(
                    conversation_retention_days=ConversationRetentionDays(
                        conversations
                    ),
                    llm_turn_retention_days=LlmTurnRetentionDays(model_records),
                ),
                client_ip_address=ClientIpAddress("203.0.113.7"),
            )
        )


def test_the_owner_sees_the_defaults_the_recordings_and_who_deletes_copies() -> None:
    bed = PrivacyBed()

    view = bed.get.run(
        PrivacySettingsQuery(user_id=bed.owner_id, business_id=bed.business.id)
    )

    assert (view.conversation_retention_days, view.llm_turn_retention_days) == (730, 30)
    assert view.recording_retention_days == bed.business.recording_retention_days
    assert view.last_purge is None
    assert view.erasure_processors == [SubProcessor.LANGFUSE, SubProcessor.ELEVENLABS]


def test_the_latest_purge_is_shown_with_what_it_removed() -> None:
    bed = PrivacyBed()
    state = bed.states.get_or_new(bed.business.id)
    state.last_run_at = Microseconds(1_790_000_000_000_000)
    state.last_counts = RetentionPurgeCounts(deleted_messages=ErasedRecordCount(12))
    bed.states.save(state)

    view = bed.get.run(
        PrivacySettingsQuery(user_id=bed.owner_id, business_id=bed.business.id)
    )

    assert view.last_purge is not None
    assert view.last_purge.ran_at == 1_790_000_000_000_000
    assert view.last_purge.counts.deleted_messages == 12


def test_a_longer_period_is_saved_and_audited_without_a_step_up() -> None:
    bed = PrivacyBed()

    bed.change(conversations=1825, model_records=30)

    stored = bed.settings.get_or_default(bed.business.id)
    assert stored.conversation_retention_days == 1825
    assert bed.step_up.checks == []
    entry = bed.testbed.audit_log_repo.list_by_business(bed.business.id)[-1]
    assert (entry.action, str(entry.entity), entry.actor_id) == (
        AuditAction.UPDATE,
        "privacy_settings",
        bed.owner_id,
    )
    assert entry.ip_address == "203.0.113.7"


@pytest.mark.parametrize(("conversations", "model_records"), [(365, 30), (730, 7)])
def test_a_shorter_period_asks_for_a_recent_sign_in_first(
    conversations: int, model_records: int
) -> None:
    bed = PrivacyBed()
    bed.step_up.is_required = True

    with pytest.raises(StepUpRequiredError):
        bed.change(conversations, model_records)
    assert (
        bed.settings.get_or_default(bed.business.id).conversation_retention_days == 730
    )

    bed.step_up.is_required = False
    bed.change(conversations, model_records)
    stored = bed.settings.get_or_default(bed.business.id)
    assert (stored.conversation_retention_days, stored.llm_turn_retention_days) == (
        conversations,
        model_records,
    )


def test_staff_can_neither_read_nor_change_the_periods() -> None:
    bed = PrivacyBed()

    with pytest.raises(AccessDeniedError):
        bed.get.run(
            PrivacySettingsQuery(user_id=bed.staff_id, business_id=bed.business.id)
        )
    with pytest.raises(AccessDeniedError):
        bed.update.run(
            UpdatePrivacySettingsCommand(
                user_id=bed.staff_id,
                business_id=bed.business.id,
                request=PrivacySettingsRequest(
                    conversation_retention_days=ConversationRetentionDays(30),
                    llm_turn_retention_days=LlmTurnRetentionDays(1),
                ),
            )
        )


@pytest.mark.parametrize(
    ("conversations", "model_records"), [(29, 30), (3651, 30), (730, 31), (730, 0)]
)
def test_periods_outside_the_promises_are_refused(
    conversations: int, model_records: int
) -> None:
    with pytest.raises(ValueError):
        PrivacySettingsRequest.model_validate(
            {
                "conversation_retention_days": conversations,
                "llm_turn_retention_days": model_records,
            }
        )
