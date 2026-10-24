"""
The Channels page's helpers over a channels testbed: checking a Telegram
token (Telegram scripted) and the per-language WhatsApp staff templates.
"""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.rate_limits.in_memory_rate_limit_bucket_adapter import (
    InMemoryRateLimitBucketAdapter,
)
from app.clients.telegram.telegram_file_client import TelegramFileClient
from app.gateways.http.channel_setup_routes import build_channel_setup_router
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.user_authentication import build_current_user_dependency
from app.registries.limits.request_rate_limit_registry import RequestRateLimitRegistry
from app.use_cases.channels.connection.validate_telegram_token_use_case import (
    ValidateTelegramTokenUseCase,
)
from app.use_cases.channels.set_whatsapp_staff_templates_use_case import (
    SetWhatsAppStaffTemplatesUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from tests.channels.cabinet_setup import CabinetSetup
from tests.channels.channels_http import wrap_use_case
from tests.channels.channels_payloads import HttpResponse, bearer, telegram_ok

BOT_TOKEN: str = "123456789:AAGuidedTelegramTokenForTheTests00000"  # gitleaks:allow
# The smallest JPEG header and some bytes: enough for the type check.
PHOTO_BYTES: bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64


class ChannelSetupWorld(CabinetSetup):
    def __init__(self) -> None:
        super().__init__()
        testbed = self.testbed
        self.telegram = testbed.telegram_transport
        self.rate_limits = RequestRateLimitRegistry(InMemoryRateLimitBucketAdapter())
        self.validate_token = ValidateTelegramTokenUseCase(
            testbed.authorize_business_access,
            testbed.telegram_client,
            TelegramFileClient(transport=self.telegram.build()),
            self.rate_limits,
            testbed.wall_clock,
        )
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_channel_setup_router(
                current_user=build_current_user_dependency(
                    testbed.authentication, SessionAssuranceContext()
                ),
                validate_telegram_token_operator=wrap_use_case(self.validate_token),
                set_whatsapp_staff_templates_operator=wrap_use_case(
                    SetWhatsAppStaffTemplatesUseCase(
                        testbed.authorize_business_access,
                        testbed.channel_repo,
                        testbed.audit_log_repo,
                        testbed.wall_clock,
                    )
                ),
            )
        )
        self.setup_client = TestClient(application)

    def check_token(self, token: str = BOT_TOKEN, user: str = "owner") -> HttpResponse:
        return self.setup_client.post(
            f"/v1/businesses/{self.business.id}/channels/telegram/validate-token",
            json={"bot_token": token},
            headers=bearer(user),
        )

    def put_templates(
        self, templates: list[dict[str, str]], user: str = "owner"
    ) -> HttpResponse:
        return self.setup_client.put(
            f"/v1/businesses/{self.business.id}/channels/whatsapp/staff-templates",
            json={"templates": templates},
            headers=bearer(user),
        )

    def script_bot(
        self,
        photos: list[list[dict[str, Any]]] | None = None,
        photo: bytes = PHOTO_BYTES,
    ) -> None:
        """A bot "Mtsvane Ezo" (@mtsvane_ezo_bot) with these profile photos."""

        self.telegram.respond(
            "POST",
            r"/getMe$",
            telegram_ok(
                {
                    "id": 7012345678,
                    "is_bot": True,
                    "first_name": "Mtsvane Ezo",
                    "username": "mtsvane_ezo_bot",
                }
            ),
        )
        self.telegram.respond(
            "POST",
            r"/getUserProfilePhotos$",
            telegram_ok({"total_count": len(photos or []), "photos": photos or []}),
        )
        self.telegram.respond(
            "POST", r"/getFile$", telegram_ok({"file_path": "photos/file_7.jpg"})
        )
        self.telegram.respond("GET", r"/file/bot.+/photos/file_7\.jpg$", photo)
