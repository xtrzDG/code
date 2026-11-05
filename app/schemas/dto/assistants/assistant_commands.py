"""
HTTP bodies and commands of assistant versions: assembly, autotests,
publishing and rollback.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.assistants import AutotestScenarioKind
from app.schemas.dto.assistants.smoke_checks import SmokeCheckSelection
from app.schemas.typings.assistants.booleans import (
    AcceptsFailedAutotests,
    ShouldRunAutotests,
)
from app.schemas.typings.assistants.prefixed_id import AssistantVersionId
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId


class AssembleAssistantVersionRequest(ImmutableDTO):
    """
    HTTP body of version assembly; every field is optional.

    `languages` and `kinds` only narrow the autotests that run right after
    the assembly; the version itself always covers every business language.
    """

    run_autotests: ShouldRunAutotests = True
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class AssembleAssistantVersionCommand(ImmutableDTO):
    """Owner assembles a new assistant version from the current profile."""

    user_id: UserId
    business_id: BusinessId
    request: AssembleAssistantVersionRequest = Field(
        default_factory=AssembleAssistantVersionRequest
    )


class AssistantVersionsQuery(ImmutableDTO):
    """List the assistant versions of a business (owners and staff)."""

    user_id: UserId
    business_id: BusinessId


class AssistantVersionQuery(ImmutableDTO):
    """Read one assistant version (owners and staff)."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId


class RunAutotestsRequest(ImmutableDTO):
    """HTTP body of an autotest run; missing lists mean "all of them"."""

    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None


class RunAutotestsCommand(ImmutableDTO):
    """
    Owner runs the autotests of one version, optionally narrowed; "Apply
    changes" runs its quick `smoke_check` instead (never from HTTP).
    """

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId
    languages: list[LanguageTag] | None = None
    kinds: list[AutotestScenarioKind] | None = None
    smoke_check: SmokeCheckSelection | None = None


class PublishAssistantVersionRequest(ImmutableDTO):
    """
    HTTP body of publishing. A version that did not pass the autotests is
    published only by a platform admin with `accept_failed_tests` set (the
    decision is written to the audit log).
    """

    accept_failed_tests: AcceptsFailedAutotests = False


class PublishAssistantVersionCommand(ImmutableDTO):
    """Owner switches the assistant to a version ("Включить")."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId
    accept_failed_tests: AcceptsFailedAutotests = False


class RollbackAssistantVersionCommand(ImmutableDTO):
    """Owner publishes an earlier, archived version again."""

    user_id: UserId
    business_id: BusinessId
    version_id: AssistantVersionId
