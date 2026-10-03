"""The platform bot webhook: link codes, staff chats and replies."""

import pytest

from app.schemas.constants.handoffs import ManagerContactChannel
from app.schemas.domain.businesses import ManagerContact
from app.schemas.typings.handoffs.strings import ManagerContactAddress, ManagerName
from app.schemas.typings.localization.constrained_strings import LanguageTag
from tests.channels.channels_settings import build_settings
from tests.channels.platform_bot_setup import STAFF_CHAT_ID, PlatformBotSetup


class TestPlatformBotWebhook:
    def test_start_with_a_valid_code_links_the_chat(self) -> None:
        setup = PlatformBotSetup()
        code = setup.create_link({"name": "Nino", "language": "ka"}).json()["code"]

        response = setup.send_to_bot(f"/start {code}")

        assert response.status_code == 200
        assert response.json() == {"result": "queued"}
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

        assert reused.json() == relinked.json() == {"result": "queued"}
        assert setup.replies()[1].startswith("This code is invalid or has expired.")
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
        } == {"queued"}
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

        assert plain.json() == {"result": "queued"}
        assert bare_start.json() == {"result": "queued"}
        assert unknown_language.json() == {"result": "queued"}
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

        assert response.json() == {"result": "queued"}
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

        assert setup.send_to_bot(f"/start {code}").json() == {"result": "queued"}
        assert len(setup.stored_business().manager_contacts) == 1
