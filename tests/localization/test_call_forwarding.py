import pytest

from app.registries.localization.call_forwarding_guide_registry import (
    CallForwardingGuideRegistry,
)
from app.schemas.constants.channels import ChannelKind, ChannelStatus
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.localization import CallForwardingCondition
from app.schemas.constants.users import LoginMethod
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.users import UserDocument
from app.schemas.dto.catalog import (
    CallForwardingInstructions,
    CallForwardingInstructionsRequest,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCode,
    CountryCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import InstructionText
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.localization.localized_text_resolver import LocalizedTextResolver
from tests.localization.builders import build_business
from tests.localization.cabinet_builders import (
    CabinetWorld,
    add_phone_channel,
    build_cabinet_world,
)

GEORGIAN_ASSISTANT_NUMBER: str = "+995322123456"


def build_georgian_world() -> tuple[CabinetWorld, BusinessDocument, UserId, UserId]:
    world = build_cabinet_world()
    owner_id, staff_id = UserId(), UserId()
    business = build_business(owner_id, "GE", "ka", staff_ids=[staff_id])
    world.business_repo.save(business)
    add_phone_channel(world, business, GEORGIAN_ASSISTANT_NUMBER)
    return world, business, owner_id, staff_id


def request_instructions(
    world: CabinetWorld,
    business: BusinessDocument,
    user_id: UserId,
    language: str | None = None,
) -> CallForwardingInstructions:
    return world.call_forwarding_operator.operate(
        CallForwardingInstructionsRequest(
            user_id=user_id,
            business_id=business.id,
            display_language=LanguageTag(language) if language is not None else None,
        )
    )


def test_georgian_owner_gets_codes_and_carriers_in_georgian() -> None:
    world, business, owner_id, _ = build_georgian_world()

    instructions = request_instructions(world, business, owner_id)

    assert instructions.display_language == "ka"
    assert instructions.country_code == "GE"
    assert instructions.assistant_phone_number == GEORGIAN_ASSISTANT_NUMBER
    assert instructions.assistant_phone_number_display == "+995 32 212 34 56"
    assert {code.condition: str(code.dial_code) for code in instructions.codes} == {
        CallForwardingCondition.NO_ANSWER: "**61*+995322123456#",
        CallForwardingCondition.BUSY: "**67*+995322123456#",
        CallForwardingCondition.UNREACHABLE: "**62*+995322123456#",
        CallForwardingCondition.CANCEL_ALL: "##002#",
    }
    assert all(
        type(code.dial_code) is CallForwardingDialCode for code in instructions.codes
    )
    assert [str(carrier.carrier_name) for carrier in instructions.carriers] == [
        "Magti",
        "Silknet",
        "Cellfie",
    ]
    for carrier in instructions.carriers:
        assert [code.dial_code for code in carrier.codes] == [
            code.dial_code for code in instructions.codes
        ]
        assert carrier.note is not None
    assert "*61" in str(instructions.carriers[0].note)
    assert "Silknet" in str(instructions.carriers[1].note)
    assert "აკრიფეთ **61*+995322123456#" in instructions.steps[1]
    assert "+995 32 212 34 56" in instructions.steps[1]
    assert any("##002#" in note for note in instructions.notes)
    assert all(type(step) is InstructionText for step in instructions.steps)
    assert all("{" not in step for step in [*instructions.steps, *instructions.notes])


@pytest.mark.parametrize(
    ("language", "expected_fragment"),
    [
        ("ru", "Наберите **61*+995322123456#"),
        ("en", "Dial **61*+995322123456#"),
        # German texts do not exist yet: English is the fallback.
        ("de", "Dial **61*+995322123456#"),
        ("ru-GE", "Наберите **61*+995322123456#"),
    ],
)
def test_instructions_follow_the_requested_language(
    language: str,
    expected_fragment: str,
) -> None:
    world, business, owner_id, _ = build_georgian_world()

    instructions = request_instructions(world, business, owner_id, language)

    assert instructions.display_language == language
    assert expected_fragment in instructions.steps[1]


def test_staff_may_read_instructions_and_strangers_may_not() -> None:
    world, business, _, staff_id = build_georgian_world()

    assert request_instructions(world, business, staff_id).codes != []
    with pytest.raises(NotFoundError):
        request_instructions(world, business, UserId())


def test_platform_admin_access_is_audited() -> None:
    world, business, _, _ = build_georgian_world()
    admin = UserDocument(
        login_method=LoginMethod.EMAIL,
        locale=LanguageTag("ru"),
        is_platform_admin=True,
    )
    world.user_repo.save(admin)

    request_instructions(world, business, admin.id, "ru")

    entries = world.audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries] == [AuditAction.ADMIN_ACCESS]


def test_other_countries_get_standard_gsm_codes_without_carriers() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "US", "en")
    world.business_repo.save(business)
    add_phone_channel(world, business, "+12125550123")

    instructions = request_instructions(world, business, owner_id)

    assert instructions.carriers == []
    assert instructions.codes[0].dial_code == "**61*+12125550123#"
    assert instructions.assistant_phone_number_display == "+1 212-555-0123"
    assert any("other codes" in note for note in instructions.notes)


def test_hebrew_owner_falls_back_to_english_texts() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "IL", "he")
    world.business_repo.save(business)
    add_phone_channel(world, business, "+97221234567")

    instructions = request_instructions(world, business, owner_id)

    assert instructions.display_language == "he"
    assert instructions.codes[0].dial_code == "**61*+97221234567#"
    assert instructions.steps[0].startswith("Take the phone")


def test_business_without_assistant_number_is_told_to_connect_the_phone() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "GE", "ka")
    world.business_repo.save(business)
    add_phone_channel(world, business, None)
    add_phone_channel(world, business, "+995322123456", status=ChannelStatus.DISABLED)
    add_phone_channel(world, business, "@vr_arena_bot", kind=ChannelKind.TELEGRAM)

    with pytest.raises(ValidationFailedError) as error_info:
        request_instructions(world, business, owner_id)

    assert "phone" in str(error_info.value)


def test_another_business_phone_channel_is_never_used() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "GE", "ka")
    other_business = build_business(UserId(), "GE", "ka")
    world.business_repo.save(business)
    world.business_repo.save(other_business)
    add_phone_channel(world, other_business, GEORGIAN_ASSISTANT_NUMBER)

    with pytest.raises(ValidationFailedError):
        request_instructions(world, business, owner_id)


def test_connected_number_is_preferred_over_a_pending_one() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "GE", "ka")
    world.business_repo.save(business)
    add_phone_channel(
        world,
        business,
        "+995322999999",
        status=ChannelStatus.PENDING,
        created_at=1_780_000_000_000_000,
    )
    add_phone_channel(
        world, business, "+995322123456", created_at=1_790_000_000_000_000
    )

    instructions = request_instructions(world, business, owner_id)

    assert instructions.assistant_phone_number == "+995322123456"


def test_invalid_stored_number_is_reported_without_parser_wording() -> None:
    world = build_cabinet_world()
    owner_id = UserId()
    business = build_business(owner_id, "GE", "ka")
    world.business_repo.save(business)
    add_phone_channel(world, business, "+995 1")

    with pytest.raises(ValidationFailedError) as error_info:
        request_instructions(world, business, owner_id)

    assert "Reconnect the phone channel" in str(error_info.value)


@pytest.mark.parametrize("country_code", ["GE", "US", "AM", "IL", "KZ", "PL", "JP"])
@pytest.mark.parametrize("language", ["en", "ru", "ka", "he"])
def test_every_guide_text_renders_with_all_placeholders(
    country_code: str,
    language: str,
) -> None:
    guide = CallForwardingGuideRegistry().get(CountryCode(country_code))
    resolver = LocalizedTextResolver()
    values = {
        "number": "+995 32 212 34 56",
        "no_answer_code": "**61*+995322123456#",
        "busy_code": "**67*+995322123456#",
        "unreachable_code": "**62*+995322123456#",
        "cancel_code": "##002#",
    }

    assert {template.condition for template in guide.code_templates} == set(
        CallForwardingCondition
    )
    texts = [*guide.steps, *guide.notes]
    texts.extend(
        carrier.notes for carrier in guide.carriers if carrier.notes is not None
    )
    for text in texts:
        for value_language in ("en", "ru", "ka"):
            assert LanguageTag(value_language) in text.values
        rendered = str(resolver.resolve(text, LanguageTag(language))).format_map(values)
        assert "{" not in rendered
