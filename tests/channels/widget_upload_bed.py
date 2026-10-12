"""
The channels testbed with the widget's upload route mounted: a live
business with its website chat switched on, and helpers that upload files
and send messages naming them, as the widget does.
"""

from typing import Any

from fastapi.testclient import TestClient

from app.gateways.http.widget_attachment_routes import build_widget_attachment_router
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.constants.channels import ChannelKind
from app.schemas.domain.message_media import InboundAttachment
from app.schemas.domain.widget_uploads import WidgetUploadDocument
from app.schemas.dto.channels.widget_uploads import AcceptedWidgetMessage
from app.schemas.dto.conversations import InboundMessage
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.conversations.strings import ChannelUserId, MessageText
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.use_cases.channels.uploads.accept_widget_upload_use_case import (
    AcceptWidgetUploadUseCase,
)
from app.use_cases.channels.uploads.admit_widget_upload_use_case import (
    AdmitWidgetUploadUseCase,
)
from tests.channels.channels_http import wrap_use_case
from tests.channels.channels_settings import build_settings
from tests.channels.test_widget import SESSION_KEY, enable_widget
from tests.channels.testbed import ChannelsTestbed

OTHER_VISITOR: str = "v1_7d1e0c5a9b2f43e8"
# Small caps, so a file over them is small too.
SMALL_MEDIA_LIMITS: dict[str, str] = {
    "MEDIA_MAX_IMAGE_BYTES": "65536",
    "MEDIA_MAX_VOICE_BYTES": "131072",
    "MEDIA_MAX_VOICE_SECONDS": "60",
}


class WidgetUploadBed:
    """A widget with uploads, over the in-memory channels testbed."""

    def __init__(self, settings: AppSettings | None = None) -> None:
        self.testbed = ChannelsTestbed(settings or build_settings(**SMALL_MEDIA_LIMITS))
        self.business = enable_widget(self.testbed)
        self.client: TestClient = self.testbed.build_http_client()
        testbed = self.testbed
        self.client.app.include_router(  # type: ignore[attr-defined]
            build_widget_attachment_router(
                admit_widget_upload_operator=wrap_use_case(
                    AdmitWidgetUploadUseCase(
                        testbed.business_repo,
                        testbed.channel_repo,
                        testbed.widget_rate_limits,
                        testbed.settings.media,
                        testbed.wall_clock,
                    )
                ),
                accept_widget_upload_operator=wrap_use_case(
                    AcceptWidgetUploadUseCase(
                        testbed.widget_upload_repo,
                        testbed.media_storage,
                        testbed.settings.media,
                        testbed.wall_clock,
                    )
                ),
            )
        )

    def upload(
        self,
        content: bytes,
        declared_type: str,
        session_key: str = SESSION_KEY,
        business_id: object | None = None,
        file_name: str = "upload",
    ) -> Any:
        return self.client.post(
            f"/v1/widget/{business_id or self.business.id}/attachments",
            files={"file": (file_name, content, declared_type)},
            headers={"X-Widget-Session-Key": session_key},
        )

    def uploaded_id(self, content: bytes, declared_type: str, **options: Any) -> str:
        response = self.upload(content, declared_type, **options)
        assert response.status_code == 201, response.text
        attachment_id: str = response.json()["attachment_id"]
        return attachment_id

    def send(
        self,
        attachment_ids: list[str],
        text: str | None = None,
        session_key: str = SESSION_KEY,
        business_id: object | None = None,
    ) -> Any:
        body: dict[str, Any] = {
            "session_key": session_key,
            "attachment_ids": attachment_ids,
        }
        if text is not None:
            body["text"] = text
        return self.client.post(
            f"/v1/widget/{business_id or self.business.id}/messages", json=body
        )

    def stored_upload(self, attachment_id: str) -> WidgetUploadDocument:
        [upload] = self.testbed.widget_upload_repo.get_many(
            BusinessId(str(self.business.id)), [WidgetUploadId(attachment_id)]
        )
        return upload

    def stored_bytes(self, attachment_id: str) -> bytes:
        upload = self.stored_upload(attachment_id)
        content: bytes = self.testbed.media_storage.files[
            (str(self.business.id), str(upload.storage_path))
        ].content
        return content

    def accepted_message(
        self,
        uploads: list[WidgetUploadDocument],
        attachments: list[InboundAttachment],
    ) -> AcceptedWidgetMessage:
        """A visitor message as accepted, ready for the inbox, naming uploads."""

        return AcceptedWidgetMessage(
            message=InboundMessage(
                business_id=self.business.id,
                channel=ChannelKind.WEB_CHAT,
                channel_user_id=ChannelUserId(SESSION_KEY),
                text=MessageText(""),
            ),
            upload_ids=[upload.id for upload in uploads],
            attachments=attachments,
        )
