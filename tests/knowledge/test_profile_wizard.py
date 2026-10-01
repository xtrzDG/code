import pytest

from app.schemas.constants.bookings import ResourceKind
from app.schemas.constants.businesses import BusinessLinkKind, Weekday
from app.schemas.constants.compliance import AuditAction
from app.schemas.constants.knowledge import KnowledgeItemKind, KnowledgeItemSource
from app.schemas.constants.niches import NicheKey, ProfileWizardStep
from app.schemas.domain.profiles import BusinessAddress, BusinessLink, OpeningInterval
from app.schemas.dto.knowledge_admin import KnowledgeItemUpsertInput
from app.schemas.dto.profiles import (
    BookingRulesInput,
    BookingRulesStepInput,
    BusinessProfileQuery,
    ChannelsStepInput,
    ContactsAndHoursStepInput,
    ContactsInput,
    FaqAndHandoffStepInput,
    FaqEntryInput,
    NicheAndLanguagesStepInput,
    NicheCatalogQuery,
    NicheTemplateQuery,
    OfferStepInput,
    ProfileAnswerInput,
    ProfileInput,
    ProfileStepInput,
    ProfileStepSaveResult,
    ProfileWizardQuery,
    SaveProfileCommand,
    SaveProfileStepCommand,
)
from app.schemas.exceptions.application_errors import (
    InvalidPhoneNumberError,
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.billing.constrained_integers import MoneyAmountMinor
from app.schemas.typings.bookings.constrained_integers import (
    MinNoticeMinutes,
    PartySize,
    SlotDurationMinutes,
)
from app.schemas.typings.businesses.constrained_integers import (
    ClosingMinuteOfDay,
    OpeningMinuteOfDay,
)
from app.schemas.typings.businesses.constrained_strings import WebLink
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.businesses.strings import AddressText
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.schemas.typings.localization.constrained_strings import (
    CurrencyCode,
    LanguageTag,
)
from app.schemas.typings.localization.strings import RawPhoneNumberInput
from app.schemas.typings.profiles.constrained_strings import (
    QuestionChoiceKey,
    QuestionKey,
)
from app.schemas.typings.profiles.strings import (
    CancellationPolicyText,
    ForbiddenRuleText,
    HandoffRuleText,
    RawProfileAnswerText,
    ToneText,
)
from app.schemas.typings.users.prefixed_id import UserId
from tests.knowledge.harness import KnowledgeHarness


def answer(key: str, text: str) -> ProfileAnswerInput:
    return ProfileAnswerInput(
        question_key=QuestionKey(key), answer=RawProfileAnswerText(text)
    )


def choices(key: str, *choice_keys: str) -> ProfileAnswerInput:
    return ProfileAnswerInput(
        question_key=QuestionKey(key),
        choice_keys=[QuestionChoiceKey(choice_key) for choice_key in choice_keys],
    )


def hours(weekday: Weekday, opens: int, closes: int) -> OpeningInterval:
    return OpeningInterval(
        weekday=weekday,
        opens_at=OpeningMinuteOfDay(opens),
        closes_at=ClosingMinuteOfDay(closes),
    )


def save_step(
    harness: KnowledgeHarness,
    business_id: BusinessId,
    step_input: ProfileStepInput,
    actor_id: UserId | None = None,
) -> ProfileStepSaveResult:
    return harness.save_profile_step.run(
        SaveProfileStepCommand(
            business_id=business_id,
            actor_id=actor_id or UserId(),
            step_input=step_input,
        )
    )


def test_catalog_lists_all_niches_in_the_requested_language() -> None:
    harness = KnowledgeHarness()

    russian = harness.list_niche_templates.run(
        NicheCatalogQuery(language=LanguageTag("ru"))
    )
    fallback = harness.list_niche_templates.run(NicheCatalogQuery())
    hebrew = harness.list_niche_templates.run(
        NicheCatalogQuery(language=LanguageTag("he"))
    )

    assert len(russian.niches) == 16
    assert russian.niches[0].name == "Рестораны и кафе"
    assert fallback.language == "en"
    assert fallback.niches[0].name == "Restaurants and cafes"
    assert hebrew.niches[0].name == "Restaurants and cafes"


def test_niche_details_resolve_questions_and_default_rules() -> None:
    harness = KnowledgeHarness()

    details = harness.get_niche_template.run(
        NicheTemplateQuery(niche_key=NicheKey.CLINIC, language=LanguageTag("ka-GE"))
    )

    assert details.niche.name == "სტომატოლოგიები და კერძო კლინიკები"
    assert details.niche.requires_legal_review is True
    assert details.questions[0].label == "რა მიმართულებებია კლინიკაში?"
    assert (
        details.default_handoff_rules[0] == "სასწრაფო სიმპტომები ან საგანგებო ვითარება"
    )
    assert len(details.default_forbidden_rules) == 4
    assert all(
        isinstance(rule, ForbiddenRuleText) for rule in details.default_forbidden_rules
    )


def test_wizard_has_six_steps_with_localized_questions_and_blank_profile() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.HOTEL, owner_language="ru")

    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))

    assert wizard.language == "ru"
    assert [step.step for step in wizard.steps] == list(ProfileWizardStep)
    assert [step.number for step in wizard.steps] == [1, 2, 3, 4, 5, 6]
    assert wizard.steps[0].title == "Ниша и языки"
    assert wizard.steps[0].questions[0].question.label == "Какой у вас тип размещения?"
    assert wizard.currency_code == "GEL"
    assert wizard.timezone == "Asia/Tbilisi"
    assert wizard.niche.booking_unit == "night"
    assert wizard.profile.is_saved is False
    assert wizard.default_handoff_rules[0] == "Жалоба во время проживания"
    assert not wizard.steps[0].is_complete
    assert not wizard.steps[1].is_complete
    assert wizard.steps[2].is_complete
    assert wizard.steps[4].is_complete


def test_wizard_falls_back_to_english_for_languages_without_texts() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code="TR",
        currency_code="TRY",
        timezone="Europe/Istanbul",
        languages=("tr", "en"),
        owner_language="tr",
    )

    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))

    assert wizard.steps[0].title == "Niche and languages"
    assert wizard.currency_code == "TRY"


def test_wizard_of_unknown_business_is_not_found() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.get_profile_wizard.run(ProfileWizardQuery(business_id=BusinessId()))


def test_steps_store_partial_progress_and_keep_other_steps() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    first = save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(
            answers_language=LanguageTag("ru"),
            answers=[answer("cuisine", "  Грузинская  ")],
        ),
    )
    second = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(
            address=BusinessAddress(
                text=AddressText(" Тбилиси, ул. Руставели 1 "),
                maps_url=WebLink("https://maps.example.com/venue"),
            ),
            hours=[hours(Weekday.MONDAY, 720, 1380), hours(Weekday.FRIDAY, 1080, 1440)],
            contacts=ContactsInput(
                public_phone_number=RawPhoneNumberInput("555 12 34 56"),
                handoff_phone_number=RawPhoneNumberInput("+995 599 12 34 56"),
            ),
        ),
    )

    assert first.step is ProfileWizardStep.NICHE_AND_LANGUAGES
    assert first.profile.is_saved is True
    assert second.profile.answers_language == "ru"
    assert [item.answer for item in second.profile.niche_answers] == ["Грузинская"]
    assert second.profile.address is not None
    assert second.profile.address.text == " Тбилиси, ул. Руставели 1 "
    assert second.profile.contacts.public_phone_number == "+995555123456"
    assert second.profile.contacts.handoff_phone_number == "+995599123456"
    assert harness.phone_number_parser.country_hints == ["GE", "GE"]
    stored = harness.get_business_profile.run(
        BusinessProfileQuery(business_id=business.id)
    )
    assert len(stored.hours) == 2
    assert stored.updated_at == harness.wall_clock.now_unix()


@pytest.mark.parametrize(
    ("country_code", "currency_code", "timezone", "raw_phone", "expected_e164"),
    [
        ("DE", "EUR", "Europe/Berlin", "030 1234567", "+49301234567"),
        ("IL", "ILS", "Asia/Jerusalem", "050-234-5678", "+972502345678"),
        ("JP", "JPY", "Asia/Tokyo", "090-1234-5678", "+819012345678"),
        ("BR", "BRL", "America/Sao_Paulo", "(11) 91234-5678", "+5511912345678"),
        ("GE", "GEL", "Asia/Tbilisi", "+1 212 555 0100", "+12125550100"),
    ],
)
def test_phones_of_any_country_are_stored_in_e164(
    country_code: str,
    currency_code: str,
    timezone: str,
    raw_phone: str,
    expected_e164: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        country_code=country_code,
        currency_code=currency_code,
        timezone=timezone,
        languages=("en",),
        owner_language="en",
    )

    result = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(
            contacts=ContactsInput(handoff_phone_number=RawPhoneNumberInput(raw_phone))
        ),
    )

    assert result.profile.contacts.handoff_phone_number == expected_e164


def test_invalid_phone_rejects_the_whole_step() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(InvalidPhoneNumberError):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(
                hours=[hours(Weekday.MONDAY, 600, 1200)],
                contacts=ContactsInput(
                    public_phone_number=RawPhoneNumberInput("12"),
                ),
            ),
        )

    assert harness.business_profile_repo.get_by_business(business.id) is None


def test_hours_validation_errors_reach_the_owner() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="overlap"):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(
                hours=[
                    hours(Weekday.MONDAY, 600, 900),
                    hours(Weekday.MONDAY, 800, 1000),
                ]
            ),
        )


def test_contact_phone_changes_are_audited_but_other_saves_are_not() -> None:
    harness = KnowledgeHarness()
    owner_id = UserId()
    business = harness.add_business(owner_id=owner_id)
    contacts = ContactsAndHoursStepInput(
        contacts=ContactsInput(handoff_phone_number=RawPhoneNumberInput("599123456"))
    )

    save_step(harness, business.id, contacts, actor_id=owner_id)
    save_step(harness, business.id, contacts, actor_id=owner_id)
    save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[answer("cuisine", "Georgian")]),
        actor_id=owner_id,
    )

    entries = harness.audit_log_repo.list_by_business(business.id)
    assert [entry.action for entry in entries] == [AuditAction.UPDATE]
    assert entries[0].actor_id == owner_id
    assert entries[0].entity == "business_profile.contacts"


def test_niche_answers_are_validated_and_normalized() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)

    result = save_step(
        harness,
        business.id,
        OfferStepInput(
            answers=[
                choices("banquets", "separate_hall"),
                answer("banquet_max_guests", "٤٠"),
                choices("dietary_options", "vegan", "vegetarian"),
                answer("kids_menu", "YES"),
                choices("outdoor_seating", "no"),
                ProfileAnswerInput(question_key=QuestionKey("live_music")),
            ]
        ),
    )

    stored = {item.question_key: item.answer for item in result.profile.niche_answers}
    assert stored == {
        "banquets": "separate_hall",
        "banquet_max_guests": "40",
        "kids_menu": "yes",
        "outdoor_seating": "no",
        "dietary_options": "vegetarian,vegan",
    }
    wizard = harness.get_profile_wizard.run(ProfileWizardQuery(business_id=business.id))
    offer_step = wizard.steps[2]
    dietary = next(
        question
        for question in offer_step.questions
        if question.question.key == "dietary_options"
    )
    assert dietary.selected_choice_keys == ["vegetarian", "vegan"]


@pytest.mark.parametrize(
    ("step_input", "message"),
    [
        (OfferStepInput(answers=[answer("unknown_question", "x")]), "does not exist"),
        (OfferStepInput(answers=[answer("cuisine", "Georgian")]), "belongs to step"),
        (
            OfferStepInput(
                answers=[answer("live_music", "Fri"), answer("live_music", "Sat")]
            ),
            "twice",
        ),
        (OfferStepInput(answers=[answer("banquet_max_guests", "-3")]), "number"),
        (OfferStepInput(answers=[answer("banquet_max_guests", "2.5")]), "number"),
        (OfferStepInput(answers=[choices("banquets", "maybe")]), "not a choice"),
        (
            OfferStepInput(answers=[choices("banquets", "no", "whole_venue")]),
            "exactly one",
        ),
        (OfferStepInput(answers=[answer("banquets", "no")]), "choice_keys"),
        (OfferStepInput(answers=[choices("live_music", "no")]), "text"),
        (OfferStepInput(answers=[answer("kids_menu", "perhaps")]), "yes"),
        (
            OfferStepInput(answers=[choices("dietary_options", "vegan", "vegan")]),
            "repeats",
        ),
        (OfferStepInput(answers=[answer("live_music", "x" * 301)]), "longer"),
    ],
)
def test_invalid_niche_answers_are_rejected(
    step_input: OfferStepInput,
    message: str,
) -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)

    with pytest.raises(ValidationFailedError, match=message):
        save_step(harness, business.id, step_input)


def test_phone_answers_use_the_business_country_as_a_hint() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(
        niche_key=NicheKey.SHORT_TERM_RENTAL,
        country_code="AM",
        currency_code="AMD",
        timezone="Asia/Yerevan",
        languages=("hy", "ru", "en"),
        owner_language="ru",
    )

    result = save_step(
        harness,
        business.id,
        ContactsAndHoursStepInput(answers=[answer("host_phone", "077 123456")]),
    )

    assert result.profile.niche_answers[0].answer == "+37477123456"


def test_offer_step_upserts_items_in_the_business_currency_without_duplicates() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    offer = OfferStepInput(
        items=[
            KnowledgeItemUpsertInput(
                kind=KnowledgeItemKind.MENU_ITEM,
                title=KnowledgeTitle("Хачапури по-аджарски"),
                price_minor=MoneyAmountMinor(1800),
            )
        ]
    )

    first = save_step(harness, business.id, offer)
    second = save_step(harness, business.id, offer)

    assert len(first.saved_knowledge_items) == 1
    assert first.saved_knowledge_items[0].currency_code == "GEL"
    assert first.saved_knowledge_items[0].formatted_price == "18,00\xa0₾"
    assert first.saved_knowledge_items[0].source is KnowledgeItemSource.PROFILE
    assert second.saved_knowledge_items[0].id == first.saved_knowledge_items[0].id
    assert len(harness.knowledge_item_repo.list_by_business(business.id)) == 1


def test_offer_step_rejects_prices_in_another_currency_and_saves_nothing() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="business currency GEL"):
        save_step(
            harness,
            business.id,
            OfferStepInput(
                items=[
                    KnowledgeItemUpsertInput(
                        kind=KnowledgeItemKind.MENU_ITEM,
                        title=KnowledgeTitle("Pizza"),
                        price_minor=MoneyAmountMinor(900),
                    ),
                    KnowledgeItemUpsertInput(
                        kind=KnowledgeItemKind.MENU_ITEM,
                        title=KnowledgeTitle("Pasta"),
                        price_minor=MoneyAmountMinor(1200),
                        currency_code=CurrencyCode("EUR"),
                    ),
                ]
            ),
        )

    assert harness.knowledge_item_repo.list_by_business(business.id) == []


def test_booking_rules_use_niche_defaults_and_the_business_currency() -> None:
    harness = KnowledgeHarness()
    hotel = harness.add_business(
        niche_key=NicheKey.HOTEL,
        country_code="JP",
        currency_code="JPY",
        timezone="Asia/Tokyo",
        languages=("ja", "en"),
        owner_language="en",
    )

    result = save_step(
        harness,
        hotel.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(4),
                min_notice_minutes=MinNoticeMinutes(120),
                deposit_minor=MoneyAmountMinor(5000),
                cancellation_policy=CancellationPolicyText("  Free until 24h  "),
            ),
            answers=[
                answer("check_in_time", "15:00"),
                answer("check_out_time", "11:00"),
            ],
        ),
    )

    rules = result.profile.booking_rules
    assert rules is not None
    assert rules.resource_kind is ResourceKind.ROOM
    assert rules.slot_minutes == 1440
    assert rules.deposit_minor == 5000
    assert rules.deposit_currency_code == "JPY"
    assert rules.cancellation_policy == "  Free until 24h  "


def test_booking_rules_reject_foreign_deposits_and_non_booking_niches() -> None:
    harness = KnowledgeHarness()
    restaurant = harness.add_business(
        country_code="FR",
        currency_code="EUR",
        timezone="Europe/Paris",
        languages=("fr", "en"),
        owner_language="fr",
    )
    shop = harness.add_business(niche_key=NicheKey.ONLINE_SHOP)

    with pytest.raises(ValidationFailedError, match="business currency EUR"):
        save_step(
            harness,
            restaurant.id,
            BookingRulesStepInput(
                booking_rules=BookingRulesInput(
                    max_party_size=PartySize(8),
                    deposit_minor=MoneyAmountMinor(1000),
                    deposit_currency_code=CurrencyCode("USD"),
                )
            ),
        )

    with pytest.raises(ValidationFailedError, match="takes no bookings"):
        save_step(
            harness,
            shop.id,
            BookingRulesStepInput(
                booking_rules=BookingRulesInput(max_party_size=PartySize(1))
            ),
        )

    defaults = save_step(
        harness,
        restaurant.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(8),
                slot_minutes=SlotDurationMinutes(30),
                deposit_minor=MoneyAmountMinor(0),
            )
        ),
    )
    assert defaults.profile.booking_rules is not None
    assert defaults.profile.booking_rules.slot_minutes == 30
    assert defaults.profile.booking_rules.deposit_minor is None
    assert defaults.profile.booking_rules.deposit_currency_code is None


def test_faq_and_handoff_step_saves_rules_tone_and_faq_items() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    result = save_step(
        harness,
        business.id,
        FaqAndHandoffStepInput(
            faq=[
                FaqEntryInput(
                    question=KnowledgeTitle("Есть ли парковка?"),
                    answer=KnowledgeBody("Да, бесплатная, во дворе"),
                    languages=[LanguageTag("ru")],
                )
            ],
            handoff_rules=[
                HandoffRuleText(" Жалоба "),
                HandoffRuleText("жалоба"),
                HandoffRuleText(""),
                HandoffRuleText("Банкет больше 20 человек"),
            ],
            forbidden=[ForbiddenRuleText("Скидки без согласования")],
            tone=ToneText("  дружелюбно и коротко "),
        ),
    )

    assert result.profile.handoff_rules == [" Жалоба ", "Банкет больше 20 человек"]
    assert result.profile.forbidden == ["Скидки без согласования"]
    assert result.profile.tone == "  дружелюбно и коротко "
    assert result.saved_knowledge_items[0].kind is KnowledgeItemKind.FAQ
    assert result.saved_knowledge_items[0].title == "Есть ли парковка?"


def test_too_long_rules_and_tone_are_rejected() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="handoff"):
        save_step(
            harness,
            business.id,
            FaqAndHandoffStepInput(handoff_rules=[HandoffRuleText("x" * 301)]),
        )

    with pytest.raises(ValidationFailedError, match="tone"):
        save_step(
            harness,
            business.id,
            FaqAndHandoffStepInput(tone=ToneText("x" * 201)),
        )


def test_channels_step_keeps_one_link_per_kind() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    menu = BusinessLink(
        kind=BusinessLinkKind.MENU, url=WebLink("https://example.ge/menu")
    )

    result = save_step(
        harness,
        business.id,
        ChannelsStepInput(links=[menu], is_recording_notice_enabled=False),
    )

    assert result.profile.links == [menu]
    assert result.profile.is_recording_notice_enabled is False
    with pytest.raises(ValidationFailedError, match="two menu links"):
        save_step(harness, business.id, ChannelsStepInput(links=[menu, menu]))


def test_full_profile_save_replaces_everything_and_validates_like_steps() -> None:
    harness = KnowledgeHarness()
    owner_id = UserId()
    business = harness.add_business(niche_key=NicheKey.BEAUTY_SALON, owner_id=owner_id)
    save_step(
        harness,
        business.id,
        ChannelsStepInput(
            links=[
                BusinessLink(
                    kind=BusinessLinkKind.BOOKING_PAGE,
                    url=WebLink("https://salon.example/book"),
                )
            ]
        ),
    )

    view = harness.save_profile.run(
        SaveProfileCommand(
            business_id=business.id,
            actor_id=owner_id,
            profile=ProfileInput(
                address=BusinessAddress(text=AddressText("Batumi, Gorgiladze 10")),
                hours=[hours(Weekday.SATURDAY, 600, 1200)],
                contacts=ContactsInput(
                    handoff_phone_number=RawPhoneNumberInput("+995 577 11 22 33")
                ),
                booking_rules=BookingRulesInput(max_party_size=PartySize(1)),
                answers=[
                    choices("service_categories", "nails", "hair"),
                    answer("break_between_appointments", "15"),
                ],
            ),
        )
    )

    assert view.links == []
    assert view.booking_rules is not None
    assert view.booking_rules.resource_kind is ResourceKind.STAFF
    assert view.booking_rules.slot_minutes == 60
    assert [item.answer for item in view.niche_answers] == ["hair,nails", "15"]
    assert view.contacts.handoff_phone_number == "+995577112233"
    assert len(harness.audit_log_repo.list_by_business(business.id)) == 1

    with pytest.raises(ValidationFailedError, match="does not exist"):
        harness.save_profile.run(
            SaveProfileCommand(
                business_id=business.id,
                actor_id=owner_id,
                profile=ProfileInput(answers=[answer("cuisine", "Georgian")]),
            )
        )


def test_answers_of_a_previous_niche_are_dropped_after_a_niche_change() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business(niche_key=NicheKey.RESTAURANT)
    save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[answer("cuisine", "Georgian")]),
    )
    business.niche_key = NicheKey.ENTERTAINMENT
    harness.business_repo.save(business)

    result = save_step(
        harness,
        business.id,
        NicheAndLanguagesStepInput(answers=[choices("venue_type", "vr_club")]),
    )

    assert result.profile.niche_key is NicheKey.ENTERTAINMENT
    assert [item.question_key for item in result.profile.niche_answers] == [
        "venue_type"
    ]


def test_profile_of_unknown_business_is_not_found() -> None:
    harness = KnowledgeHarness()

    with pytest.raises(NotFoundError):
        harness.get_business_profile.run(BusinessProfileQuery(business_id=BusinessId()))

    with pytest.raises(NotFoundError):
        save_step(harness, BusinessId(), NicheAndLanguagesStepInput())


def test_blank_texts_are_rejected_or_cleared() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()

    with pytest.raises(ValidationFailedError, match="address is empty"):
        save_step(
            harness,
            business.id,
            ContactsAndHoursStepInput(address=BusinessAddress(text=AddressText("  "))),
        )

    result = save_step(
        harness,
        business.id,
        FaqAndHandoffStepInput(
            tone=ToneText("   "),
            forbidden=[ForbiddenRuleText(" "), ForbiddenRuleText("No discounts")],
        ),
    )
    rules = save_step(
        harness,
        business.id,
        BookingRulesStepInput(
            booking_rules=BookingRulesInput(
                max_party_size=PartySize(2),
                cancellation_policy=CancellationPolicyText(" "),
            )
        ),
    )

    assert result.profile.tone is None
    assert result.profile.forbidden == ["No discounts"]
    assert rules.profile.booking_rules is not None
    assert rules.profile.booking_rules.cancellation_policy is None
