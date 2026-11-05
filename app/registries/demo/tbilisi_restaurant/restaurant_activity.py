"""The month of activity of the Tbilisi demo restaurant."""

from app.contracts.registries import PlanRegistryContract
from app.registries.demo.demo_activity_builder import DemoActivityBuilder
from app.registries.demo.demo_autotests import finished_run
from app.registries.demo.demo_billing import trial_subscription
from app.registries.demo.tbilisi_restaurant.restaurant_autotests import (
    build_restaurant_autotest_results,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_en_bookings import (
    record_english_booking_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_en_questions import (
    record_english_question_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_ka_bookings import (
    record_georgian_booking_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_ka_questions import (
    record_georgian_question_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_media import (
    record_media_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_rtl import (
    record_rtl_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_ru_bookings import (
    record_russian_booking_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_ru_questions import (
    record_russian_question_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_chats_ru_requests import (
    record_russian_request_chats,
)
from app.registries.demo.tbilisi_restaurant.restaurant_desk import record_front_desk
from app.registries.demo.tbilisi_restaurant.restaurant_guests import register_guests
from app.schemas.constants.compliance import AuditAction
from app.schemas.domain.compliance import AuditLogEntryDocument
from app.schemas.dto.demo_data import DemoActivityRequest, DemoBusinessActivity
from app.schemas.typings.compliance.strings import (
    AuditEntityName,
    AuditEntityReference,
)

# The trial started 12 days ago; its package usage is what the seeded
# chats and calls of these 12 days metered (DemoActivityBuilder.finish).
TRIAL_DAYS_AGO: int = -12


def build_restaurant_activity(
    request: DemoActivityRequest, plan_registry: PlanRegistryContract
) -> DemoBusinessActivity:
    story = DemoActivityBuilder(request)
    guests = register_guests(story)
    for record in (
        record_georgian_booking_chats,
        record_georgian_question_chats,
        record_russian_booking_chats,
        record_russian_request_chats,
        record_russian_question_chats,
        record_english_booking_chats,
        record_english_question_chats,
        record_rtl_chats,
        record_media_chats,
        record_front_desk,
    ):
        record(story, guests)

    clock = story.clock
    subscription = trial_subscription(
        plan_registry, story.business, clock.past(TRIAL_DAYS_AGO, "10:30")
    )
    published = next(
        plan
        for plan in request.foundation.assistant_versions
        if plan.published_at is not None and plan.test_score is None
    )
    return story.finish(
        subscription=subscription,
        autotest_run=finished_run(
            story.business.id,
            story.published_version_id,
            clock.later(published.created_at, 14),
            build_restaurant_autotest_results(),
        ),
        audit_log_entries=build_audit_entries(story),
    )


def build_audit_entries(story: DemoActivityBuilder) -> list[AuditLogEntryDocument]:
    """The owner and the hall manager read conversation cards and a contact."""

    clock = story.clock
    entries: list[AuditLogEntryDocument] = []
    for index, conversation in enumerate(story.talk.conversations[:6]):
        moment = clock.later(conversation.last_message_at, 20 + index * 7)
        if moment >= clock.now:
            continue

        entries.append(
            AuditLogEntryDocument(
                business_id=story.business.id,
                actor_id=story.owner_id if index % 2 == 0 else story.team_member_id,
                action=AuditAction.VIEW,
                entity=AuditEntityName("conversation"),
                entity_id=AuditEntityReference(str(conversation.id)),
                created_at=moment,
                updated_at=moment,
            )
        )

    exported = story.talk.contacts[0]
    moment = clock.past(-6, "11:05")
    entries.append(
        AuditLogEntryDocument(
            business_id=story.business.id,
            actor_id=story.owner_id,
            action=AuditAction.EXPORT,
            entity=AuditEntityName("contact"),
            entity_id=AuditEntityReference(str(exported.id)),
            created_at=moment,
            updated_at=moment,
        )
    )
    return entries
