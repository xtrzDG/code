"""
Erasing a customer deletes the originals of the photos and voice notes
they sent through the website chat (kept a day under widget-uploads/ beside
the message's own copy) and their widget_uploads rows; another customer's
uploads stay. Before, both outlived the erasure until the daily purge.
"""

from uuid import NAMESPACE_URL, uuid5

from typed_time_provider import Microseconds

from app.schemas.constants.channels import ChannelKind
from app.schemas.constants.deliveries import InboundEventKind, InboundEventStatus
from app.schemas.constants.media import AttachmentKind
from app.schemas.domain.inbound_events import (
    InboundCustomerMessage,
    InboundEventDocument,
)
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.compliance import ContactDataCommand
from app.schemas.dto.media import MediaLocation, StoredMediaFile
from app.schemas.typings.channels.prefixed_id import WidgetVisitorId
from app.schemas.typings.channels.strings import ProviderMessageId
from app.schemas.typings.conversations.strings import MessageText
from app.schemas.typings.deliveries.prefixed_id import InboundEventId
from app.schemas.typings.media.constrained_integers import MediaByteCount
from app.schemas.typings.media.constrained_strings import MessageMediaType
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.schemas.typings.media.strings import ProviderMediaId, ProviderMediaType
from app.utilities.media.media_paths import widget_upload_storage_path
from tests.compliance.customer_records import seed_customers
from tests.compliance.visitor_records import SeededVisitor
from tests.media.media_fakes import jpeg_bytes
from tests.users.accounts_testbed import AccountsTestbed

JPEG: MessageMediaType = MessageMediaType("image/jpeg")


def sent_through_the_widget(
    testbed: AccountsTestbed, visitor: SeededVisitor
) -> WidgetUploadDocument:
    """A photo the visitor uploaded, and the website chat message naming it."""

    business_id = visitor.contact.business_id
    now: Microseconds = testbed.clock.now_microseconds()
    upload_id = WidgetUploadId()
    path = widget_upload_storage_path(business_id, upload_id, JPEG)
    testbed.media_storage.store(
        MediaLocation(business_id=business_id, path=path),
        StoredMediaFile(content=jpeg_bytes(), media_type=JPEG),
    )
    upload = WidgetUploadDocument(
        id=upload_id,
        business_id=business_id,
        visitor_id=WidgetVisitorId(),
        kind=AttachmentKind.IMAGE,
        media_type=JPEG,
        storage_path=path,
        byte_count=MediaByteCount(len(jpeg_bytes())),
        attached_at=now,
        created_at=now,
        updated_at=now,
    )
    testbed.widget_upload_repo.save(upload)
    testbed.inbound_event_repo.insert_if_new(
        InboundEventDocument(
            id=InboundEventId(uuid5(NAMESPACE_URL, f"widget-{upload_id}")),
            business_id=business_id,
            kind=InboundEventKind.CUSTOMER_MESSAGE,
            channel=ChannelKind.WEB_CHAT,
            provider_message_id=ProviderMessageId(f"widget-{upload_id}"),
            customer_message=InboundCustomerMessage(
                channel_user_id=visitor.chat_conversation.channel_user_id,
                text=MessageText("Here is the photo of the cake I want."),
                attachments=[
                    InboundAttachment(
                        kind=AttachmentKind.IMAGE,
                        provider_media_id=ProviderMediaId(str(path)),
                        mime_type=ProviderMediaType(str(JPEG)),
                    )
                ],
            ),
            status=InboundEventStatus.ANSWERED,
            created_at=now,
            updated_at=now,
        )
    )
    return upload


def test_erasing_a_customer_removes_their_widget_uploads() -> None:
    customers = seed_customers()
    testbed = customers.testbed
    business_id = customers.business.id
    giorgis = sent_through_the_widget(testbed, customers.giorgi)
    ninos = sent_through_the_widget(testbed, customers.nino)

    testbed.delete_contact_data.run(
        ContactDataCommand(
            user_id=customers.owner_id,
            business_id=business_id,
            contact_id=customers.giorgi.contact.id,
        )
    )

    gone = MediaLocation(business_id=business_id, path=giorgis.storage_path)
    kept = MediaLocation(business_id=business_id, path=ninos.storage_path)
    assert testbed.media_storage.read(gone) is None
    assert testbed.widget_upload_repo.get_many(business_id, [giorgis.id]) == []
    assert testbed.media_storage.read(kept) is not None
    assert testbed.widget_upload_repo.get_many(business_id, [ninos.id]) == [ninos]
