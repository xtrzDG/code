"""
What a customer scenario prepares before its conversation: the persona as
a WhatsApp contact with a proven phone, a booking to come made by the
product's own use case, an earlier summarized conversation with the
team's note on it and an open order, another customer for an attacker to
ask about, and the media of the first message (a voice note's transcript
or a photo kept in the run's memory).
"""

from pathlib import Path

import pytest
from typed_time_provider import Microseconds

from app.containers.app import AppContainer
from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.conversations import ConversationStatus
from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.media import AttachmentKind
from app.schemas.dto.media import MediaLocation
from app.schemas.typings.assistants.constrained_strings import LlmModelId
from app.schemas.typings.bookings.constrained_integers import BookingSearchBoundSeconds
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.localization.constrained_strings import E164PhoneNumber
from app.schemas.typings.storage.constrained_integers import DocumentQueryLimit
from scripts.eval_harness.business_seeding import EvalBusinessSeeder, SeededBusiness
from scripts.eval_harness.catalog_seeding import CatalogSpec, build_catalog
from scripts.eval_harness.dataset_loading import load_dataset
from scripts.eval_harness.dataset_models import ScenarioSpec
from scripts.eval_harness.dataset_setup_models import AttachmentSpec
from scripts.eval_harness.eval_container import (
    SteppingClock,
    SwitchableLlmAdapter,
    build_environment,
    build_eval_container,
)
from scripts.eval_harness.media_inputs import FirstMessageMedia
from scripts.eval_harness.scenario_seeding import (
    customer_channel_user_id,
    seed_customer,
)
from tests.evals.test_dataset_files import DATASETS

PHONE: str = "+447911123456"
OTHER_PHONE: str = "+995599112233"
NOTE: str = "Regular guest, prefers the corner table."


type World = tuple[AppContainer, EvalBusinessSeeder, SeededBusiness]


@pytest.fixture(scope="module")
def world() -> World:
    container = build_eval_container(
        build_environment(LlmModelId("scripted"), {}),
        SteppingClock(),
        SwitchableLlmAdapter(),
    )
    seeder = EvalBusinessSeeder(container)
    dataset = load_dataset(DATASETS / "beauty_salon.yaml")
    return container, seeder, seeder.seed(dataset.niche, dataset.business)


def spec(**fields: object) -> ScenarioSpec:
    values: dict[str, object] = {
        "id": "returning__en",
        "language": "en",
        "kind": "returning_customer",
        "channel": "whatsapp",
        "persona": {"name": "Emma", "phone": PHONE},
        "goal": "Come back.",
        "customer": ["Hi again!"],
        "assistant": [{"say": "Welcome back!"}],
    }
    values.update(fields)
    return ScenarioSpec.model_validate(values)


def test_a_customer_comes_with_a_booking_a_memory_and_a_neighbour(
    world: World,
) -> None:
    container, seeder, seeded = world
    business_id = seeded.business.id
    repositories = container.repositories
    # The owner's test chat is a sandbox: nobody is seeded for it.
    seed_customer(
        container,
        seeded,
        spec(channel="owner_test", kind="price_question"),
        seeder.owner_id,
    )
    with container.utilities.storage_scope().scoped_to_business(business_id):
        assert repositories.contact_repo().list_by_business(business_id) == []

    seed_customer(
        container,
        seeded,
        spec(
            setup={
                "booking": {"date": "2026-10-08", "time": "13:00", "party_size": 1},
                "earlier": {
                    "summary": "Asked about a haircut.",
                    "note": NOTE,
                    "lead": "Bridal hair trial",
                },
                "other_customer": {
                    "name": "Giorgi Beridze",
                    "phone": OTHER_PHONE,
                    "booking": {"date": "2026-10-08", "time": "15:00", "party_size": 1},
                },
            }
        ),
        seeder.owner_id,
    )

    with container.utilities.storage_scope().scoped_to_business(business_id):
        contact = repositories.contact_repo().find_by_channel_identity(
            business_id, ChannelKind.WHATSAPP, ChannelUserId("447911123456")
        )
        assert contact is not None
        assert contact.verified_phone_number == E164PhoneNumber(PHONE)
        other = repositories.contact_repo().find_by_verified_phone_number(
            business_id, E164PhoneNumber(OTHER_PHONE)
        )
        assert other is not None and other.name == "Giorgi Beridze"
        bookings = repositories.booking_repo().list_ending_after(
            business_id, BookingSearchBoundSeconds(0)
        )
        assert sorted(booking.contact_id for booking in bookings) == sorted(
            [contact.id, other.id]
        )
        earlier = repositories.conversation_repo().list_latest_by_contact(
            business_id, contact.id, DocumentQueryLimit(5)
        )
        assert [item.status for item in earlier] == [ConversationStatus.CLOSED]
        assert str(earlier[0].summary) == "Asked about a haircut."
        notes = repositories.conversation_note_repo().list_by_conversation(
            business_id, earlier[0].id
        )
        assert [str(note.text) for note in notes] == [NOTE]
        leads = repositories.lead_repo().list_by_conversation(
            business_id, earlier[0].id
        )
        assert [str(lead.details) for lead in leads] == ["Bridal hair trial"]
        settings = repositories.assistant_settings_repo().get_by_business(business_id)
        assert settings is not None and settings.shares_team_notes


def test_a_voice_note_carries_its_transcript_and_a_photo_its_bytes(
    world: World, tmp_path: Path
) -> None:
    container, _, seeded = world
    storage = container.adapters.media.media_storage()
    (tmp_path / "salon.png").write_bytes(b"\x89PNG-test")

    def media(attachment: AttachmentSpec) -> FirstMessageMedia:
        return FirstMessageMedia(
            attachment=attachment,
            storage=storage,
            business_id=seeded.business.id,
            media_dir=tmp_path,
        )

    text, [voice] = media(AttachmentSpec(voice_note=True)).deliver(
        MessageText("Hi, how much is a women's haircut, please?")
    )
    assert text == ""
    assert voice.kind is AttachmentKind.AUDIO
    assert str(voice.transcript) == "Hi, how much is a women's haircut, please?"
    assert voice.duration_seconds == 3

    text, [photo] = media(AttachmentSpec(photo="salon.png")).deliver(
        MessageText("How much is this?")
    )
    assert text == "How much is this?"
    assert photo.kind is AttachmentKind.IMAGE and photo.media_type == "image/png"
    assert photo.storage_path is not None
    location = MediaLocation(business_id=seeded.business.id, path=photo.storage_path)
    stored = storage.read(location)
    assert stored is not None and stored.content == b"\x89PNG-test"
    storage.delete(location)
    assert storage.read(location) is None


def test_a_whatsapp_user_id_is_the_number_without_the_plus() -> None:
    assert customer_channel_user_id("+995 555 10-02-01") == "995555100201"


def test_a_catalog_numbers_its_items_at_one_price(world: World) -> None:
    _, _, seeded = world
    items = build_catalog(
        seeded.business,
        CatalogSpec(title="Blend No. {n}", body="Tea {n}.", price="12", count=3),
        KnowledgeItemKind.SERVICE,
        Microseconds(0),
    )

    assert [(str(item.title), str(item.body)) for item in items] == [
        ("Blend No. 1", "Tea 1."),
        ("Blend No. 2", "Tea 2."),
        ("Blend No. 3", "Tea 3."),
    ]
    assert {item.price_minor for item in items} == {1200}
    assert {item.kind for item in items} == {KnowledgeItemKind.SERVICE}
