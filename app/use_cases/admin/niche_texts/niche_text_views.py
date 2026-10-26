"""The views of the niche template editor, built from its documents."""

from app.contracts.localization_utilities import LocalizedTextResolverContract
from app.contracts.repositories.user_repositories import UserRepoContract
from app.schemas.constants.niches import NicheKey
from app.schemas.domain.niche_texts import (
    NicheTextDraftDocument,
    NicheTextReleaseDocument,
)
from app.schemas.dto.niche_texts.niche_text_fields import (
    NicheTextCatalog,
    NicheTextChoice,
    NicheTextQuestion,
)
from app.schemas.dto.niche_texts.niche_text_views import (
    NicheTextChoiceView,
    NicheTextEditorView,
    NicheTextFieldView,
    NicheTextQuestionView,
    NicheTextReleaseView,
    NicheTextStatusView,
)
from app.schemas.dto.niches import NicheTemplate
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.niches.constrained_integers import (
    NicheOverrideCount,
    NicheTextVersion,
)
from app.schemas.typings.niches.constrained_strings import (
    NicheOverrideText,
    NicheTextFieldKey,
)
from app.schemas.typings.users.strings import UserDisplayName
from app.use_cases.admin.niche_texts.niche_text_editing import (
    NicheTextSources,
    display_names,
    is_unpublished,
    published_entries,
)
from app.utilities.knowledge.localized_texts import FALLBACK_LANGUAGE_TAG
from app.utilities.niches.niche_text_checks import EDITABLE_LANGUAGES
from app.utilities.niches.niche_text_overlay import overlay_niche_template

type TextsByField = dict[NicheTextFieldKey, NicheOverrideText]


def load_editor_view(
    sources: NicheTextSources,
    user_repo: UserRepoContract,
    resolver: LocalizedTextResolverContract,
    niche_key: NicheKey,
    language: LanguageTag,
) -> NicheTextEditorView:
    """The editor of a niche in `language` as stored now."""

    release: NicheTextReleaseDocument | None = sources.latest(niche_key)
    draft: NicheTextDraftDocument | None = sources.niche_text_repo.get_draft(niche_key)
    names = display_names(user_repo, [] if release is None else [release.published_by])
    status: NicheTextStatusView = status_view(
        sources.niche_templates.get(niche_key),
        language,
        release,
        draft,
        None if release is None else names.get(release.published_by),
        resolver,
    )
    return editor_view(
        sources.catalog(niche_key), language, status, release, draft, resolver
    )


def status_view(
    template: NicheTemplate,
    language: LanguageTag,
    release: NicheTextReleaseDocument | None,
    draft: NicheTextDraftDocument | None,
    publisher_name: UserDisplayName | None,
    resolver: LocalizedTextResolverContract,
) -> NicheTextStatusView:
    """The niche's state, named as owners read it now."""

    effective: NicheTemplate = overlay_niche_template(
        template, published_entries(release)
    )
    return NicheTextStatusView(
        niche_key=template.key,
        name=resolver.resolve(effective.names, language),
        published_version=NicheTextVersion(
            0 if release is None else int(release.version)
        ),
        override_count=NicheOverrideCount(len(published_entries(release))),
        published_at=None if release is None else release.created_at,
        published_by_name=publisher_name,
        has_draft=is_unpublished(draft, release),
        draft_override_count=NicheOverrideCount(
            0 if draft is None else len(draft.entries)
        ),
    )


def editor_view(
    catalog: NicheTextCatalog,
    language: LanguageTag,
    status: NicheTextStatusView,
    release: NicheTextReleaseDocument | None,
    draft: NicheTextDraftDocument | None,
    resolver: LocalizedTextResolverContract,
) -> NicheTextEditorView:
    """Every editable text in `language` beside the code's own wording."""

    published: TextsByField = texts_in(release, language)
    drafted: TextsByField = texts_in(draft, language)
    return NicheTextEditorView(
        niche_key=catalog.niche_key,
        language=language,
        languages=list(EDITABLE_LANGUAGES),
        status=status,
        fields=[
            NicheTextFieldView(
                field_key=field.field_key,
                section=field.section,
                question_key=field.question_key,
                code_text=field.code_texts.values.get(language),
                english_text=field.code_texts.values[FALLBACK_LANGUAGE_TAG],
                published_text=published.get(field.field_key),
                draft_text=drafted.get(field.field_key),
                max_length=field.max_length,
            )
            for field in catalog.fields
        ],
        questions=[
            question_view(question, language, resolver)
            for question in catalog.questions
        ],
    )


def question_view(
    question: NicheTextQuestion,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> NicheTextQuestionView:
    return NicheTextQuestionView(
        key=question.key,
        step=question.step,
        answer_type=question.answer_type,
        is_required=question.is_required,
        label_field=question.label_field,
        hint_field=question.hint_field,
        choices=[
            choice_view(choice, language, resolver) for choice in question.choices
        ],
    )


def choice_view(
    choice: NicheTextChoice,
    language: LanguageTag,
    resolver: LocalizedTextResolverContract,
) -> NicheTextChoiceView:
    return NicheTextChoiceView(
        key=choice.key,
        field_key=choice.field_key,
        fixed_label=(
            None
            if choice.fixed_labels is None
            else resolver.resolve(choice.fixed_labels, language)
        ),
    )


def release_view(
    release: NicheTextReleaseDocument, publisher_name: UserDisplayName | None
) -> NicheTextReleaseView:
    return NicheTextReleaseView(
        niche_key=release.niche_key,
        version=release.version,
        kind=release.kind,
        override_count=NicheOverrideCount(len(release.entries)),
        restored_version=release.restored_version,
        published_at=release.created_at,
        published_by=release.published_by,
        published_by_name=publisher_name,
    )


def texts_in(
    document: NicheTextReleaseDocument | NicheTextDraftDocument | None,
    language: LanguageTag,
) -> TextsByField:
    if document is None:
        return {}

    return {
        entry.field_key: entry.text
        for entry in document.entries
        if entry.language == language
    }
