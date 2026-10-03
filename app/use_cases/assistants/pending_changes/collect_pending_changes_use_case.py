from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.transformer_contract import TransformerContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.constants.setup import PendingChangeAction, PendingChangeArea
from app.schemas.domain.assistants import AssistantVersionDocument
from app.schemas.dto.assistants.assembly_sources import AssistantInstructionSource
from app.schemas.dto.assistants.assistant_drafts import (
    AssistantDraft,
    AssistantDraftRequest,
)
from app.schemas.dto.setup.pending_changes import PendingChange, PendingChangesRequest
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.utilities.assembly.fact_diff import diff_fact_tables


class CollectPendingChangesUseCase(
    UseCaseContract[PendingChangesRequest, list[PendingChange]]
):
    """
    What the owner changed that `version` does not have: the assistant is
    built again from the business as it is now (nothing is stored) and its
    fact table compared with the version's, row by row (see
    `diff_fact_tables`). Two more changes are not rows: the phone line
    that comes with the plan or goes (CALLS), and how the assistant talks
    (tone, what it never says, when it calls a person), which only the
    instruction holds: when no row changed but the profile was saved after
    the version was built, the instruction is composed again with the
    version's own facts and compared (CONVERSATION). A platform update of
    the instruction templates alone is therefore not the owner's change.

    Raises:
        ValidationFailedError: the business has no profile.
    """

    def __init__(
        self,
        build_assistant_draft: UseCaseContract[AssistantDraftRequest, AssistantDraft],
        assistant_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ],
        localized_text_resolver: LocalizedTextResolverContract,
    ) -> None:
        self._build_assistant_draft: UseCaseContract[
            AssistantDraftRequest, AssistantDraft
        ] = build_assistant_draft
        self._assistant_instruction_transformer: TransformerContract[
            AssistantInstructionSource,
            SystemPromptText,
        ] = assistant_instruction_transformer
        self._resolver: LocalizedTextResolverContract = localized_text_resolver

    def run(self, input_data: PendingChangesRequest) -> list[PendingChange]:
        version: AssistantVersionDocument = input_data.version
        draft: AssistantDraft = self._build_assistant_draft.run(
            AssistantDraftRequest(business=input_data.business)
        )
        changes: list[PendingChange] = diff_fact_tables(
            version.facts,
            draft.facts,
            draft.today,
            self._answer_labels(draft, input_data.language),
        )
        if draft.is_voice_enabled != version.is_voice_enabled:
            changes.append(
                PendingChange(
                    area=PendingChangeArea.CALLS,
                    action=(
                        PendingChangeAction.ADDED
                        if draft.is_voice_enabled
                        else PendingChangeAction.REMOVED
                    ),
                )
            )

        if not changes and self._has_new_conversation_rules(draft, version):
            changes.append(
                PendingChange(
                    area=PendingChangeArea.CONVERSATION,
                    action=PendingChangeAction.CHANGED,
                )
            )

        return changes

    def _answer_labels(
        self, draft: AssistantDraft, language: LanguageTag
    ) -> dict[str, str]:
        """The niche questions in the owner's words, by the fact key they fill."""

        return {
            str(question.fact_key): str(
                self._resolver.resolve(question.labels, language)
            )
            for question in draft.instruction_source.niche.questions
        }

    def _has_new_conversation_rules(
        self,
        draft: AssistantDraft,
        version: AssistantVersionDocument,
    ) -> bool:
        if int(draft.profile_revision) <= int(version.profile_revision):
            return False

        with_version_facts: AssistantInstructionSource = (
            draft.instruction_source.model_copy(update={"facts": list(version.facts)})
        )
        return (
            self._assistant_instruction_transformer.transform(with_version_facts)
            != version.prompt_text
        )
