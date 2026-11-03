"""
Knowledge items that name a customer (PRIV-08): the customer's export lists
them, by name or by number in any format, and their erasure flags them for
the owner without changing the owner's text; an owner's save of the item
clears the flag.
"""

from typed_time_provider import Microseconds

from app.schemas.constants.knowledge import KnowledgeItemKind
from app.schemas.constants.privacy import KnowledgeMentionMatch
from app.schemas.domain.businesses import BusinessDocument
from app.schemas.domain.knowledge import KnowledgeItemDocument
from app.schemas.dto.compliance import ContactRecordsQuery
from app.schemas.dto.knowledge_admin import (
    KnowledgeItemPatch,
    UpdateKnowledgeItemCommand,
)
from app.schemas.typings.knowledge.strings import KnowledgeBody, KnowledgeTitle
from app.utilities.knowledge.knowledge_item_views import to_item_details
from tests.compliance.two_tenants import TwoTenants, command, seed_two_tenants
from tests.knowledge.harness import KnowledgeHarness
from tests.knowledge.knowledge_base_helpers import add_item


def stored_item(
    tenants: TwoTenants,
    business: BusinessDocument,
    title: str,
    body: str | None = None,
) -> KnowledgeItemDocument:
    item = KnowledgeItemDocument(
        business_id=business.id,
        kind=KnowledgeItemKind.FAQ,
        title=KnowledgeTitle(title),
        body=None if body is None else KnowledgeBody(body),
    )
    tenants.testbed.knowledge_item_repo.save(item)
    return item


class MentioningItems:
    """The visitor Giorgi (+995 577 123456) and items about him and others."""

    def __init__(self) -> None:
        self.tenants = seed_two_tenants()
        business = self.tenants.business
        self.by_name = stored_item(self.tenants, business, "Table for GIORGI")
        self.by_number = stored_item(
            self.tenants,
            business,
            "Catering",
            "Call back on 0577 12-34-56 for the order.",
        )
        self.by_both = stored_item(
            self.tenants, business, "Regulars", "Giórgi, +995577123456"
        )
        self.longer_word = stored_item(self.tenants, business, "Giorgione pizza")
        self.neighbour = stored_item(self.tenants, business, "Ask Nino")
        self.short_number = stored_item(
            self.tenants, business, "Prices", "Set menu 123456, wine 577"
        )
        self.other_business = stored_item(
            self.tenants,
            self.tenants.testbed.business_repo.get(
                self.tenants.foreign_visitor.contact.business_id
            )
            or business,
            "Giorgi",
        )


def test_the_export_lists_the_items_that_name_the_customer() -> None:
    world = MentioningItems()

    export = world.tenants.testbed.export_contact_data.run(
        command(world.tenants, world.tenants.visitor.contact.id)
    )

    mentions = {
        mention.knowledge_item_id: mention.matched_on
        for mention in export.records.knowledge_mentions
    }
    assert mentions == {
        world.by_name.id: [KnowledgeMentionMatch.NAME],
        world.by_number.id: [KnowledgeMentionMatch.PHONE],
        world.by_both.id: [KnowledgeMentionMatch.NAME, KnowledgeMentionMatch.PHONE],
    }
    (catering,) = [
        mention
        for mention in export.records.knowledge_mentions
        if mention.knowledge_item_id == world.by_number.id
    ]
    assert catering.body == "Call back on 0577 12-34-56 for the order."


def test_the_erasure_flags_the_items_and_keeps_the_owners_text() -> None:
    world = MentioningItems()
    repo = world.tenants.testbed.knowledge_item_repo
    business_id = world.tenants.business.id
    now = world.tenants.testbed.clock.now_microseconds()

    result = world.tenants.testbed.delete_contact_data.run(
        command(world.tenants, world.tenants.visitor.contact.id)
    )

    assert int(result.flagged_knowledge_items) == 3
    for flagged in (world.by_name, world.by_number, world.by_both):
        stored = repo.get(business_id, flagged.id)
        assert stored is not None
        assert stored.erased_customer_flagged_at == now
        assert (stored.title, stored.body) == (flagged.title, flagged.body)
    for untouched in (world.longer_word, world.neighbour, world.short_number):
        stored = repo.get(business_id, untouched.id)
        assert stored == untouched
    other = repo.get(world.other_business.business_id, world.other_business.id)
    assert other is not None
    assert other.erased_customer_flagged_at is None


def test_the_erasure_applied_again_keeps_the_first_flag() -> None:
    world = MentioningItems()
    testbed = world.tenants.testbed
    business_id = world.tenants.business.id
    records = testbed.collect_contact_records.run(
        ContactRecordsQuery(
            business_id=business_id, contact_id=world.tenants.visitor.contact.id
        )
    )
    first = testbed.clock.now_microseconds()
    testbed.contact_data_eraser.erase(records, first)
    testbed.clock.advance(60)

    # After a restore the same records are erased again.
    again = testbed.contact_data_eraser.erase(records, testbed.clock.now_microseconds())

    stored = testbed.knowledge_item_repo.get(business_id, world.by_name.id)
    assert stored is not None
    assert stored.erased_customer_flagged_at == first
    assert int(again.flagged_knowledge_items) == 3


def test_the_owner_sees_the_flag_and_a_save_clears_it() -> None:
    harness = KnowledgeHarness()
    business = harness.add_business()
    details = add_item(harness, business, "Regulars", kind=KnowledgeItemKind.FAQ)
    stored = harness.knowledge_item_repo.get(business.id, details.id)
    assert stored is not None
    flagged = stored.model_copy(
        update={"erased_customer_flagged_at": Microseconds(1_000)}
    )
    harness.knowledge_item_repo.save(flagged)

    shown = to_item_details(flagged, business.currency_code, business.owner_language)
    saved = harness.update_knowledge_item.run(
        UpdateKnowledgeItemCommand(
            business_id=business.id,
            item_id=details.id,
            patch=KnowledgeItemPatch(body=KnowledgeBody("Our regular guests.")),
        )
    )

    assert shown.erased_customer_flagged_at == 1_000
    assert saved.erased_customer_flagged_at is None
    after = harness.knowledge_item_repo.get(business.id, details.id)
    assert after is not None
    assert after.erased_customer_flagged_at is None
