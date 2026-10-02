from typing import Any

import httpx
import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import BusinessDocument, ManagerContact
from app.schemas.dto.channels.staff_links import PlatformBotWebhookSetup
from app.schemas.exceptions.application_errors import ExternalServiceError
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from app.schemas.typings.platform.strings import PlatformSecret
from app.use_cases.channels.configure_platform_bot_webhook_use_case import (
    ConfigurePlatformBotWebhookUseCase,
)
from app.utilities.channels.channel_endpoints import TELEGRAM_SECRET_HEADER
from app.utilities.channels.webhook_signatures import derive_telegram_webhook_secret
from tests.channels.testbed import (
    ENCRYPTION_KEY,
    GEORGIA,
    PLATFORM_BOT_TOKEN,
    ChannelsTestbed,
    HttpResponse,
    bearer,
    build_settings,
    telegram_ok,
    to_json_bytes,
)

PLATFORM_SECRET: str = str(
    derive_telegram_webhook_secret(
        PlatformSecret(ENCRYPTION_KEY), PlatformSecret(PLATFORM_BOT_TOKEN)
    )
)
STAFF_CHAT_ID: int = 31_337


class PlatformBotSetup:
    def __init__(self, settings: Any = None) -> None:
        self.testbed = ChannelsTestbed(settings)
        self.owner_id = self.testbed.add_user("owner")
        self.staff_id = self.testbed.add_user("staff")
        self.business: BusinessDocument = self.testbed.add_business(
            self.owner_id,
            country=GEORGIA,
            staff_ids=[self.staff_id],
            owner_language="ru",
        )
        self.client = self.testbed.build_http_client()
        self.testbed.telegram_transport.respond(
            "POST", r"/getMe$", telegram_ok({"username": "workshop_staff_bot"})
        )
        self.testbed.telegram_transport.respond(
            "POST", r"/sendMessage$", telegram_ok({})
        )

    def create_link(self, body: dict[str, Any], token: str = "owner") -> HttpResponse:
        return self.client.post(
            f"/v1/businesses/{self.business.id}/manager-contacts/telegram-link",
            json=body,
            headers=bearer(token),
        )

    def send_to_bot(
        self,
        text: str,
        secret: str | None = PLATFORM_SECRET,
        chat_type: str = "private",
        language_code: str = "en",
    ) -> HttpResponse:
        update = {
            "update_id": 1,
            "message": {
                "message_id": 5,
                "chat": {"id": STAFF_CHAT_ID, "type": chat_type},
                "from": {
                    "id": STAFF_CHAT_ID,
                    "is_bot": False,
                    "language_code": language_code,
                },
                "text": text,
            },
        }
        headers = {} if secret is None else {TELEGRAM_SECRET_HEADER: secret}
        return self.client.post(
            "/v1/channels/telegram-platform/webhook",
            content=to_json_bytes(update),
            headers=headers,
        )

    def replies(self) -> list[str]:
        return [
            str(request.json()["text"])
            for request in self.testbed.telegram_transport.requests_to("/sendMessage")
        ]

    def stored_business(self) -> BusinessDocument:
        business = self.testbed.business_repo.get(self.business.id)
        assert business is not None
        return business


class TestTelegramLinkCreation:
    def test_owner_gets_a_one_time_code_and_deep_link(self) -> None:
        setup = PlatformBotSetup()

        response = setup.create_link({"name": "Levan"})

        assert response.status_code == 201
        body = response.json()
        code: str = body["code"]
        assert len(code) == 10
        assert body["bot_username"] == "workshop_staff_bot"
        assert body["deep_link"] == f"https://t.me/workshop_staff_bot?start={code}"
        assert (
            body["expires_at"] == setup.testbed.clock.now_microseconds() + 1_800_000_000
        )
        [link] = setup.testbed.link_repo.list_by_business(setup.business.id)
        assert link.language == "ru"
        assert code not in str(link.code_hash)

    def test_staff_cannot_create_links_and_input_is_checked(self) -> None:
        setup = PlatformBotSetup()

        assert setup.create_link({"name": "Levan"}, token="staff").status_code == 403
        assert setup.create_link({"name": "   "}).status_code == 422
        assert setup.create_link({"name": "x" * 101}).status_code == 422
        assert setup.create_link({"name": "Levan", "language": "xx"}).status_code == 422

    def test_without_the_platform_bot_nothing_is_created(self) -> None:
        setup = PlatformBotSetup(build_settings(TELEGRAM_PLATFORM_BOT_TOKEN=""))

        assert setup.create_link({"name": "Levan"}).status_code == 502
        assert setup.testbed.link_repo.list_by_business(setup.business.id) == []

    def test_unreachable_bot_still_gives_the_code(self) -> None:
        setup = PlatformBotSetup()
        setup.testbed.telegram_transport.failure = httpx.ConnectError("down")

        body = setup.create_link({"name": "Levan"}).json()

        assert body["deep_link"] is None
        assert len(body["code"]) == 10


class TestPlatformBotWebhook:
    def test_start_with_a_valid_code_links_the_chat(self) -> None:
        setup = PlatformBotSetup()
        code = setup.create_link({"name": "Nino", "language": "ka"}).json()["code"]

        response = setup.send_to_bot(f"/start {code}")

        assert response.status_code == 200
        assert response.json() == {"result": "linked"}
        [manager] = setup.stored_business().manager_contacts
        assert manager.channel is ManagerContactChannel.TELEGRAM
        assert manager.address == str(STAFF_CHAT_ID)
        assert manager.name == "Nino"
        assert manager.language == "ka"
        assert setup.replies()[-1].startswith("კავშირი დამყარდა: Funicular VR.")
        assert ("update", "manager_contacts") in setup.testbed.audit_actions(
            setup.business.id
        )

    def test_a_code_works_once_and_relinking_replaces_the_contact(self) -> None:
        setup = PlatformBotSetup()
        first_code = setup.create_link({"name": "Nino"}).json()["code"]
        setup.send_to_bot(f"/start {first_code}")

        reused = setup.send_to_bot(f"/start {first_code}")
        second_code = setup.create_link({"name": "Nino B."}).json()["code"]
        relinked = setup.send_to_bot(f"/start {second_code.lower()}")

        assert reused.json() == {"result": "rejected_code"}
        assert relinked.json() == {"result": "linked"}
        assert [
            contact.name for contact in setup.stored_business().manager_contacts
        ] == ["Nino B."]

    def test_expired_and_unknown_codes_are_explained_in_the_sender_language(
        self,
    ) -> None:
        setup = PlatformBotSetup()
        code = setup.create_link({"name": "Nino"}).json()["code"]
        setup.testbed.clock.advance(31 * 60)

        expired = setup.send_to_bot(f"/start {code}", language_code="uk")
        unknown = setup.send_to_bot("/start 0000000000", language_code="he")
        malformed = setup.send_to_bot("/start <script>", language_code="ar")

        assert {
            expired.json()["result"],
            unknown.json()["result"],
            malformed.json()["result"],
        } == {"rejected_code"}
        replies = setup.replies()
        assert replies[0].startswith("Код недійсний")
        assert replies[1].startswith("הקוד אינו תקף")
        assert replies[2].startswith("هذا الرمز غير صالح")
        assert setup.stored_business().manager_contacts == []

    def test_other_messages_get_instructions(self) -> None:
        setup = PlatformBotSetup()

        plain = setup.send_to_bot("hello", language_code="pt-br")
        bare_start = setup.send_to_bot("/start", language_code="kk")
        unknown_language = setup.send_to_bot("/help", language_code="tlh")

        assert plain.json() == {"result": "instructions_sent"}
        assert bare_start.json() == {"result": "instructions_sent"}
        assert unknown_language.json() == {"result": "instructions_sent"}
        replies = setup.replies()
        assert replies[0].startswith("Olá!")
        assert replies[1].startswith("Сәлеметсіз бе!")
        assert replies[2].startswith("Hello!")

    def test_groups_and_bots_are_ignored(self) -> None:
        setup = PlatformBotSetup()
        code = setup.create_link({"name": "Nino"}).json()["code"]

        response = setup.send_to_bot(f"/start {code}", chat_type="group")

        assert response.json() == {"result": "ignored"}
        assert setup.stored_business().manager_contacts == []

    def test_contact_limit_keeps_the_code(self) -> None:
        setup = PlatformBotSetup()
        business = setup.stored_business()
        business.manager_contacts = [
            ManagerContact(
                name=ManagerName(f"Staff {index}"),
                channel=ManagerContactChannel.EMAIL,
                address=ManagerContactAddress(f"staff{index}@example.ge"),
                language=LanguageTag("en"),
            )
            for index in range(20)
        ]
        setup.testbed.business_repo.save(business)
        code = setup.create_link({"name": "Nino"}).json()["code"]

        response = setup.send_to_bot(f"/start {code}")

        assert response.json() == {"result": "contact_limit_reached"}
        assert setup.replies()[-1].startswith("У «Funicular VR» уже максимальное")
        [link] = setup.testbed.link_repo.list_by_business(setup.business.id)
        assert link.used_at is None

    @pytest.mark.parametrize("secret", [None, "wrong"])
    def test_webhook_secret_is_required(self, secret: str | None) -> None:
        setup = PlatformBotSetup()

        assert setup.send_to_bot("/start X", secret=secret).status_code == 401

    def test_unconfigured_platform_bot_is_not_found(self) -> None:
        setup = PlatformBotSetup(build_settings(TELEGRAM_PLATFORM_BOT_TOKEN=""))

        assert setup.send_to_bot("/start X").status_code == 404

    def test_reply_failures_do_not_undo_the_link(self) -> None:
        setup = PlatformBotSetup()
        code = setup.create_link({"name": "Nino"}).json()["code"]
        setup.testbed.telegram_transport.respond(
            "POST",
            r"/sendMessage$",
            {"ok": False, "error_code": 403, "description": "blocked"},
            status_code=403,
        )

        assert setup.send_to_bot(f"/start {code}").json() == {"result": "linked"}
        assert len(setup.stored_business().manager_contacts) == 1


class TestPlatformBotSetup:
    def test_webhook_is_registered_with_the_derived_secret(self) -> None:
        testbed = ChannelsTestbed()
        testbed.telegram_transport.respond(
            "POST", r"/getMe$", telegram_ok({"username": "workshop_staff_bot"})
        )
        testbed.telegram_transport.respond("POST", r"/setWebhook$", telegram_ok())

        profile = ConfigurePlatformBotWebhookUseCase(
            testbed.telegram_client, testbed.settings
        ).run(PlatformBotWebhookSetup())

        assert profile.username == "workshop_staff_bot"
        [request] = testbed.telegram_transport.requests_to("/setWebhook")
        assert request.json()["url"] == (
            "https://api.workshop.test/v1/channels/telegram-platform/webhook"
        )
        assert request.json()["secret_token"] == PLATFORM_SECRET

    def test_missing_settings_are_reported(self) -> None:
        for overrides in (
            {"TELEGRAM_PLATFORM_BOT_TOKEN": ""},
            {"APP_BASE_URL": ""},
            {"APP_BASE_URL": "http://localhost:8000"},
        ):
            testbed = ChannelsTestbed(build_settings(**overrides))
            testbed.telegram_transport.respond(
                "POST", r"/getMe$", telegram_ok({"username": "bot_name"})
            )
            with pytest.raises(ExternalServiceError):
                ConfigurePlatformBotWebhookUseCase(
                    testbed.telegram_client, testbed.settings
                ).run(PlatformBotWebhookSetup())
