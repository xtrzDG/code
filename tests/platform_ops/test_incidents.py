"""
POST /v1/admin/incidents' use case: an incident is stored with one audit
entry per affected business; a data breach tells every owner of those
businesses (not their staff, not other businesses) in the owner's language,
by e-mail or else SMS; the admin must have signed in recently.
"""

import json

import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.dto.incidents import CreateIncidentBody, CreateIncidentCommand
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.exceptions.mfa_errors import StepUpRequiredError
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.platform_ops.incident_world import RU_OWNER, IncidentWorld, breach
from tests.platform_ops.ops_documents import DAY, HOUR, at, business
from tests.platform_ops.ops_world import ADMIN, put


def test_a_breach_tells_every_owner_of_the_affected_business_only() -> None:
    world = IncidentWorld()

    view = world.use_case.run(breach(world.salon))

    assert int(view.notified_owner_count) == 2 and view.notified_at is not None
    by_channel = {sent.contact.channel: sent for sent in world.notifier.sent}
    assert set(by_channel) == {ManagerContactChannel.EMAIL, ManagerContactChannel.SMS}
    email, sms = (
        by_channel[ManagerContactChannel.EMAIL],
        by_channel[ManagerContactChannel.SMS],
    )
    assert str(email.contact.address) == "nino@salon.example"
    assert str(sms.contact.address) == "+995555123456"
    assert {sent.business_id for sent in world.notifier.sent} == {world.salon.id}
    assert str(email.subject) == f"incident:{view.id}"
    # Neither Russian nor Georgian is a cabinet language any more: both
    # owners read the English frame with the team's English texts.
    assert str(email.text).startswith("Personal data breach notice: Salon Ia")
    assert "An export was e-mailed wrongly." in str(email.text)
    assert str(sms.text).startswith("Personal data breach notice: Salon Ia")
    assert "An export was e-mailed wrongly." in str(sms.text)
    assert "(Asia/Tbilisi)" in str(sms.text)


def test_an_italian_owner_reads_the_italian_frame_with_the_english_texts() -> None:
    world = IncidentWorld()
    italian = RU_OWNER.model_copy(update={"locale": LanguageTag("it-IT")})
    put(world.users, italian)

    world.use_case.run(breach(world.salon))

    [email] = [
        sent
        for sent in world.notifier.sent
        if sent.contact.channel is ManagerContactChannel.EMAIL
    ]
    text = str(email.text)
    assert text.startswith("Avviso di violazione dei dati personali: Salon Ia")
    # The team wrote English and Georgian texts: Italian reads the English ones.
    assert "Cosa è successo: An export was e-mailed wrongly." in text
    assert "Persone interessate: Customers, circa 40" in text
    assert "(punto 12.2)" in text and "{" not in text


def test_each_affected_business_gets_an_audit_entry_naming_the_incident() -> None:
    world = IncidentWorld()

    view = world.use_case.run(breach(world.salon, world.cafe))

    entries = world.audit.list_all()
    assert sorted(str(entry.business_id) for entry in entries) == sorted(
        [str(world.salon.id), str(world.cafe.id)]
    )
    assert {str(entry.entity_id) for entry in entries} == {str(view.id)}
    assert {entry.actor_id for entry in entries} == {ADMIN}
    assert int(view.notified_owner_count) == 3
    [stored] = world.incidents.list_all()
    assert stored.affected_business_ids == [world.salon.id, world.cafe.id]


def test_an_outage_is_recorded_without_notices() -> None:
    world = IncidentWorld()
    outage = CreateIncidentCommand(
        user_id=ADMIN,
        body=CreateIncidentBody.model_validate_json(
            json.dumps(
                {
                    "kind": "outage",
                    "severity": "sev2",
                    "title": "Replies delayed",
                    "started_at": int(at(-HOUR)),
                    "affected_business_ids": [str(world.salon.id)],
                }
            )
        ),
    )

    view = world.use_case.run(outage)

    assert world.notifier.sent == []
    assert int(view.notified_owner_count) == 0 and view.notified_at is None
    assert len(world.audit.list_all()) == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"started_at": int(at(HOUR))},
        {"detected_at": int(at(-3 * HOUR))},
        {"detected_at": int(at(DAY))},
    ],
)
def test_the_timeline_must_make_sense(changes: dict[str, object]) -> None:
    world = IncidentWorld()

    with pytest.raises(ValidationFailedError):
        world.use_case.run(breach(world.salon, **changes))

    assert world.incidents.list_all() == [] and world.notifier.sent == []


def test_an_unknown_business_refuses_the_whole_incident() -> None:
    world = IncidentWorld()
    gone = business("Closed")

    with pytest.raises(ValidationFailedError, match=str(gone.id)):
        world.use_case.run(breach(world.salon, gone))

    assert world.incidents.list_all() == [] and world.audit.list_all() == []


def test_a_stale_session_must_sign_in_again() -> None:
    world = IncidentWorld(is_recent=False)

    with pytest.raises(StepUpRequiredError):
        world.use_case.run(breach(world.salon))

    assert world.incidents.list_all() == []


@pytest.mark.parametrize(
    "changes",
    [
        {"notice_texts": []},
        {"approximate_record_count": None},
        {"affected_business_ids": []},
        {"kind": "outage"},
    ],
)
def test_a_breach_body_needs_its_dpa_fields(changes: dict[str, object]) -> None:
    world = IncidentWorld()

    with pytest.raises(ValueError):
        breach(world.salon, **changes)
