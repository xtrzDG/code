"""
The platform admin's niche template editor: a draft per niche and language,
published as a numbered version after a fresh confirmation and audited
platform-wide; the newest version is what new owners read; a revert or a
reset is just the next version.
"""

import pytest

from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.niches import NicheKey, NicheTextReleaseKind
from app.schemas.dto.niche_texts.niche_text_commands import (
    NicheTextCommand,
    NicheTextHistoryQuery,
    NicheTextOverviewQuery,
)
from app.schemas.exceptions.application_errors import (
    AccessDeniedError,
    ConflictError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.users.prefixed_id import UserId
from app.use_cases.admin.niche_texts.niche_text_releases import (
    NicheTextPublication,
    publish_release,
)
from tests.niche_texts.niche_text_world import (
    CUISINE_LABEL,
    EN,
    IP,
    RESTAURANT,
    RU,
    NicheTextWorld,
)
from tests.platform_ops.ops_world import ADMIN

NEW_LABEL = "Какую кухню вы готовите?"


def cuisine_label(world: NicheTextWorld, language: str = "ru") -> str:
    template = world.effective_templates.get(RESTAURANT)
    return str(template.questions[0].labels.values[LanguageTag(language)])


def test_the_overview_lists_every_niche_on_the_code_template() -> None:
    world = NicheTextWorld()

    overview = world.list_use_case().run(
        NicheTextOverviewQuery(user_id=ADMIN, language=RU)
    )

    assert [item.niche_key for item in overview.items] == [
        template.key for template in world.code_templates.list_all()
    ]
    first = overview.items[0]
    assert str(first.name) == "Рестораны и кафе"
    assert (int(first.published_version), int(first.override_count)) == (0, 0)
    assert first.has_draft is False


def test_the_editor_shows_the_codes_wording_and_the_questions() -> None:
    editor = NicheTextWorld().editor()

    label = next(field for field in editor.fields if field.field_key == CUISINE_LABEL)
    assert str(label.code_text) == "Какая у вас кухня?"
    assert str(label.english_text) == "What cuisine do you serve?"
    assert (label.published_text, label.draft_text) == (None, None)
    assert [str(tag) for tag in editor.languages] == ["ka", "ru", "en", "he", "de"]
    assert editor.questions[0].label_field == CUISINE_LABEL
    kids_menu = next(q for q in editor.questions if str(q.key) == "kids_menu")
    assert [str(choice.fixed_label) for choice in kids_menu.choices] == ["Да", "Нет"]


def test_a_draft_is_invisible_to_owners_until_it_is_published() -> None:
    world = NicheTextWorld()

    editor = world.save(RU, questions__cuisine__label=NEW_LABEL)

    label = next(field for field in editor.fields if field.field_key == CUISINE_LABEL)
    assert str(label.draft_text) == NEW_LABEL
    assert editor.status.has_draft is True
    assert cuisine_label(world) == "Какая у вас кухня?"

    release = world.publish()

    assert (int(release.version), release.kind) == (1, NicheTextReleaseKind.PUBLISH)
    assert int(release.override_count) == 1
    assert release.published_by == ADMIN
    assert cuisine_label(world) == NEW_LABEL
    assert cuisine_label(world, "en") == "What cuisine do you serve?"
    assert world.repo.get_draft(RESTAURANT) is None
    status = world.editor().status
    assert (int(status.published_version), status.has_draft) == (1, False)


def test_saving_one_language_keeps_the_drafts_other_languages() -> None:
    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)

    world.save(EN, questions__cuisine__label="Which cuisine do you cook?")
    world.save(RU, questions__cuisine__hint="Например: грузинская.")

    draft = world.repo.get_draft(RESTAURANT)
    assert draft is not None
    assert [(str(e.field_key), str(e.language)) for e in draft.entries] == [
        ("questions.cuisine.label", "en"),
        ("questions.cuisine.hint", "ru"),
    ]


def test_a_draft_back_at_the_published_texts_is_dropped() -> None:
    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)
    world.publish()

    world.save(RU, questions__cuisine__label="Другая кухня?")
    editor = world.save(RU, questions__cuisine__label=NEW_LABEL)

    assert world.repo.get_draft(RESTAURANT) is None
    assert editor.status.has_draft is False
    with pytest.raises(ConflictError):
        world.publish()


def test_a_draft_is_discarded_and_nothing_is_published_without_one() -> None:
    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)

    world.discard_use_case().run(NicheTextCommand(user_id=ADMIN, niche_key=RESTAURANT))

    assert world.repo.get_draft(RESTAURANT) is None
    with pytest.raises(ConflictError, match="no draft"):
        world.publish()


def test_publishing_needs_a_fresh_confirmation_and_is_audited() -> None:
    stale = NicheTextWorld(is_recent=False)
    stale.save(RU, questions__cuisine__label=NEW_LABEL)
    with pytest.raises(StepUpRequiredError):
        stale.publish()
    assert stale.releases.list_all() == []

    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)
    world.publish()
    world.revert(0)

    entries = world.audit_entries()
    assert [
        (entry.action, str(entry.entity), str(entry.entity_id)) for entry in entries
    ] == [
        (AuditAction.UPDATE, "niche_template", "restaurant:v1:publish"),
        (AuditAction.UPDATE, "niche_template", "restaurant:v2:reset"),
    ]
    assert all(
        entry.actor_id == ADMIN and entry.business_id is None for entry in entries
    )
    assert all(entry.ip_address == IP for entry in entries)


def test_a_revert_publishes_an_earlier_versions_texts_again() -> None:
    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)
    world.publish()
    world.save(RU, questions__cuisine__label="Третья кухня?")
    world.publish()

    reverted = world.revert(1)
    reset = world.revert(0)

    assert (
        int(reverted.version),
        reverted.kind,
        int(reverted.restored_version or 0),
    ) == (
        3,
        NicheTextReleaseKind.REVERT,
        1,
    )
    assert (int(reset.version), reset.kind, reset.restored_version) == (
        4,
        NicheTextReleaseKind.RESET,
        None,
    )
    assert cuisine_label(world) == "Какая у вас кухня?"
    history = world.history_use_case().run(
        NicheTextHistoryQuery(user_id=ADMIN, niche_key=RESTAURANT)
    )
    assert [int(item.version) for item in history.items] == [4, 3, 2, 1]
    assert {item.published_by_name for item in history.items} == {world.admin_name}


def test_a_revert_to_the_version_in_force_or_an_unknown_one_is_refused() -> None:
    world = NicheTextWorld()
    with pytest.raises(ConflictError, match="Version 0 is in force"):
        world.revert(0)

    world.save(RU, questions__cuisine__label=NEW_LABEL)
    world.publish()
    with pytest.raises(ConflictError, match="Version 1 is in force"):
        world.revert(1)
    with pytest.raises(NotFoundError):
        world.revert(7)


def test_a_concurrent_publish_of_the_same_version_stores_one() -> None:
    world = NicheTextWorld()
    world.save(RU, questions__cuisine__label=NEW_LABEL)
    world.publish()

    # Another admin read "no version yet" before version 1 was stored.
    with pytest.raises(ConflictError, match="published a moment ago"):
        publish_release(
            world.repo,
            world.audit_repo,
            None,
            NicheTextPublication(
                niche_key=RESTAURANT,
                kind=NicheTextReleaseKind.PUBLISH,
                entries=[],
                admin_id=ADMIN,
                client_ip_address=None,
                now=world.now(),
            ),
        )

    assert len(world.releases.list_all()) == 1
    assert len(world.audit_entries()) == 1


def test_only_admins_who_manage_niche_templates_use_the_editor() -> None:
    world = NicheTextWorld()
    stranger = UserId()

    with pytest.raises(AccessDeniedError):
        world.list_use_case().run(NicheTextOverviewQuery(user_id=stranger))
    with pytest.raises(AccessDeniedError):
        world.discard_use_case().run(
            NicheTextCommand(user_id=stranger, niche_key=NicheKey.HOTEL)
        )


def test_the_editor_speaks_only_the_cabinets_languages() -> None:
    with pytest.raises(ValidationFailedError, match="cabinet's languages"):
        NicheTextWorld().editor(language=LanguageTag("tr"))
