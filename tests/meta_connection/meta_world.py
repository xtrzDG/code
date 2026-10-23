"""
An owner, a staff member and their business behind the routes of Meta's
self-serve connection, with Meta's Graph API scripted on the channels
testbed's recording transport (no network).
"""

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.storage.in_memory_document_collection import (
    InMemoryDocumentCollectionAdapter,
)
from app.clients.meta.meta_oauth_client import MetaOAuthClient
from app.clients.meta.meta_pages_client import MetaPagesClient
from app.clients.meta.whatsapp_onboarding_client import WhatsAppOnboardingClient
from app.contracts.session_assurance import StepUpGuardContract
from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.meta_connection_routes import build_meta_connection_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.repositories.meta_connection_state_repository import (
    MetaConnectionStateRepository,
)
from app.schemas.configurations.app_settings import AppSettings
from app.schemas.domain.meta_connections import MetaConnectionStateDocument
from app.use_cases.channels.comment_replies.set_instagram_comment_replies_use_case import (  # noqa: E501
    SetInstagramCommentRepliesUseCase,
)
from app.use_cases.channels.meta_connection.complete_whatsapp_embedded_signup_use_case import (  # noqa: E501
    CompleteWhatsAppEmbeddedSignupUseCase,
)
from app.use_cases.channels.meta_connection.connect_meta_page_use_case import (
    ConnectMetaPageUseCase,
)
from app.use_cases.channels.meta_connection.get_meta_sign_in_options_use_case import (
    GetMetaSignInOptionsUseCase,
)
from app.use_cases.channels.meta_connection.list_meta_pages_use_case import (
    ListMetaPagesUseCase,
)
from app.use_cases.channels.meta_connection.start_meta_connection_use_case import (
    StartMetaConnectionUseCase,
)
from app.utilities.security.session_assurance_context import SessionAssuranceContext
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.cabinet_setup import CabinetSetup
from tests.channels.channels_http import wrap_use_case
from tests.channels.channels_payloads import HttpResponse, bearer
from tests.channels.channels_settings import build_settings
from tests.foundation.access_support import AllowStepUp
from tests.meta_connection.meta_graph_scripts import META_APP_ID, SIGNUP_CONFIG_ID


def meta_settings(**overrides: str) -> AppSettings:
    """The testbed's settings with the platform's Meta app and signup set up."""

    return build_settings(
        **{
            "META_APP_ID": META_APP_ID,
            "META_EMBEDDED_SIGNUP_CONFIG_ID": SIGNUP_CONFIG_ID,
            **overrides,
        }
    )


class MetaWorld(CabinetSetup):
    def __init__(
        self,
        settings: AppSettings | None = None,
        step_up: StepUpGuardContract | None = None,
    ) -> None:
        super().__init__(settings or meta_settings())
        step_up = step_up or AllowStepUp()
        testbed = self.testbed
        self.graph = testbed.meta_transport
        self.state_repo = MetaConnectionStateRepository(
            InMemoryDocumentCollectionAdapter(MetaConnectionStateDocument)
        )
        oauth = MetaOAuthClient(transport=self.graph.build())
        pages = MetaPagesClient(transport=self.graph.build())
        writes: dict[str, Any] = {
            "channel_repo": testbed.channel_repo,
            "secret_cipher": testbed.secret_cipher,
            "audit_log_repo": testbed.audit_log_repo,
            "product_events": testbed.product_events,
            "storage_scope": StorageScopeContext(),
            "app_settings": testbed.settings,
            "wall_clock": testbed.wall_clock,
        }
        self.complete_signup = CompleteWhatsAppEmbeddedSignupUseCase(
            testbed.authorize_business_access,
            self.state_repo,
            oauth,
            WhatsAppOnboardingClient(transport=self.graph.build()),
            **writes,
        )
        self.connect_page = ConnectMetaPageUseCase(
            testbed.authorize_business_access,
            self.state_repo,
            oauth,
            pages,
            testbed.meta_client,
            step_up=step_up,
            **writes,
        )
        application = FastAPI()
        install_error_handlers(application)
        application.include_router(
            build_meta_connection_router(
                current_user=build_current_user_dependency(
                    testbed.authentication, SessionAssuranceContext()
                ),
                sign_in_options_operator=wrap_use_case(
                    GetMetaSignInOptionsUseCase(
                        testbed.authorize_business_access, testbed.settings
                    )
                ),
                start_meta_connection_operator=wrap_use_case(
                    StartMetaConnectionUseCase(
                        testbed.authorize_business_access,
                        self.state_repo,
                        step_up,
                        testbed.settings,
                        testbed.wall_clock,
                    )
                ),
                complete_whatsapp_signup_operator=wrap_use_case(self.complete_signup),
                list_meta_pages_operator=wrap_use_case(
                    ListMetaPagesUseCase(
                        testbed.authorize_business_access,
                        self.state_repo,
                        oauth,
                        pages,
                        testbed.secret_cipher,
                        testbed.settings,
                        testbed.wall_clock,
                    )
                ),
                connect_meta_page_operator=wrap_use_case(self.connect_page),
                set_comment_replies_operator=wrap_use_case(
                    SetInstagramCommentRepliesUseCase(
                        testbed.authorize_business_access,
                        testbed.channel_repo,
                        testbed.audit_log_repo,
                        testbed.wall_clock,
                    )
                ),
            )
        )
        self.http = TestClient(application)

    @property
    def base(self) -> str:
        return f"/v1/businesses/{self.business.id}/channels"

    def sign_in_options(self, user: str = "owner") -> HttpResponse:
        return self.http.get(f"{self.base}/meta/sign-in", headers=bearer(user))

    def start(self, purpose: str, user: str = "owner") -> HttpResponse:
        return self.http.post(
            f"{self.base}/meta/sign-in", json={"purpose": purpose}, headers=bearer(user)
        )

    def started_state(self, purpose: str) -> str:
        response = self.start(purpose)
        assert response.status_code == 201, response.text
        return str(response.json()["state"])

    def complete(self, body: dict[str, Any], user: str = "owner") -> HttpResponse:
        return self.http.post(
            f"{self.base}/whatsapp/embedded-signup", json=body, headers=bearer(user)
        )

    def list_pages(self, body: dict[str, Any], user: str = "owner") -> HttpResponse:
        return self.http.post(
            f"{self.base}/meta/pages", json=body, headers=bearer(user)
        )

    def pick_page(
        self, channel: str, body: dict[str, Any], user: str = "owner"
    ) -> HttpResponse:
        return self.http.put(
            f"{self.base}/{channel}/page", json=body, headers=bearer(user)
        )

    def set_comment_replies(
        self, body: dict[str, Any], user: str = "owner"
    ) -> HttpResponse:
        return self.http.put(
            f"{self.base}/instagram/comment-replies", json=body, headers=bearer(user)
        )
