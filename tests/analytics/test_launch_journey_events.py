"""
An owner's way through the real API leaves its product events: sign-up,
business, a skipped tunnel step, the agreement, a blocked and a successful
launch, going live and the trial; once-only steps are stored once.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.analytics import (
    ProductEventName,
    ProductEventSource,
    TunnelStepKey,
)
from app.schemas.constants.setup import ApplyAttentionCode
from app.schemas.domain.product_events import ProductEventDocument
from tests.e2e.harness import Workshop
from tests.e2e.journeys import GEORGIAN_OWNER_PHONE
from tests.setup.launch_steps import (
    NewAssistant,
    accept_dpa,
    add_staff_contact,
    apply_changes,
    create_assistant,
    fill_profile,
    go_live,
    read_setup,
)

FAR_FUTURE: Microseconds = Microseconds(10**17)


def stored_events(workshop: Workshop) -> list[ProductEventDocument]:
    return workshop.container.repositories.product_event_repo().list_named(
        list(ProductEventName), None, FAR_FUTURE
    )


def named(
    events: list[ProductEventDocument], name: ProductEventName
) -> list[ProductEventDocument]:
    return [event for event in events if event.name is name]


def skip_channels(workshop: Workshop, assistant: NewAssistant) -> None:
    skipped = workshop.client.put(
        f"{assistant.base}/setup/skipped-steps/channels", headers=assistant.headers
    )
    assert skipped.status_code == 200, skipped.text


def test_the_way_to_live_is_recorded_step_by_step(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    skip_channels(workshop, assistant)
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)
    blocked = apply_changes(workshop, assistant)
    assert blocked["stage"] == "needs_attention"
    accept_dpa(workshop, assistant)

    go_live(workshop, assistant)
    read_setup(workshop, assistant)

    events = stored_events(workshop)
    business_id = assistant.business_id
    [signed_up] = named(events, ProductEventName.SIGNED_UP)
    assert str(signed_up.user_id) == assistant.owner_id
    [created] = named(events, ProductEventName.BUSINESS_CREATED)
    assert str(created.user_id) == assistant.owner_id
    assert str(created.business_id) == business_id
    [skipped] = named(events, ProductEventName.TUNNEL_STEP_SKIPPED)
    assert skipped.properties.tunnel_step is TunnelStepKey.CHANNELS
    [launch_blocked] = named(events, ProductEventName.LAUNCH_BLOCKED)
    assert ApplyAttentionCode.AGREEMENT_NOT_ACCEPTED in (
        launch_blocked.properties.attention_codes
    )
    assert len(named(events, ProductEventName.DPA_ACCEPTED)) == 1
    assert len(named(events, ProductEventName.LAUNCH_SUCCEEDED)) == 1
    [went_live] = named(events, ProductEventName.WENT_LIVE)
    [trial] = named(events, ProductEventName.TRIAL_STARTED)
    assert trial.properties.trial_ends_at is not None
    assert {str(event.business_id) for event in (went_live, trial)} == {business_id}
    assert all(event.source is ProductEventSource.SERVER for event in events)


def test_once_only_steps_are_stored_once(workshop: Workshop) -> None:
    assistant = create_assistant(workshop)
    fill_profile(workshop, assistant)
    add_staff_contact(workshop, assistant)
    accept_dpa(workshop, assistant)
    go_live(workshop, assistant)

    for _ in range(3):
        read_setup(workshop, assistant)
    workshop.clock.advance(60)
    workshop.sign_in_with_phone(GEORGIAN_OWNER_PHONE)

    events = stored_events(workshop)
    assert len(named(events, ProductEventName.WENT_LIVE)) == 1
    assert len(named(events, ProductEventName.SIGNED_UP)) == 1
    assert len(named(events, ProductEventName.SIGNED_IN)) == 2
