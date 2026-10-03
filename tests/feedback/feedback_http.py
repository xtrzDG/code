"""Settings → Reviews and the public review link over a feedback setup."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.review_routes import build_review_router
from app.gateways.http.user_authentication import build_current_user_dependency
from app.schemas.typings.channels.constrained_strings import PublicBaseUrl
from app.use_cases.feedback.links.open_review_link_use_case import (
    OpenReviewLinkUseCase,
)
from app.use_cases.feedback.settings.get_review_settings_use_case import (
    GetReviewSettingsUseCase,
)
from app.use_cases.feedback.settings.get_review_stats_use_case import (
    GetReviewStatsUseCase,
)
from app.use_cases.feedback.settings.list_feedback_requests_use_case import (
    ListFeedbackRequestsUseCase,
)
from app.use_cases.feedback.settings.update_review_settings_use_case import (
    UpdateReviewSettingsUseCase,
)
from app.utilities.storage.storage_scope_context import StorageScopeContext
from tests.channels.channels_http import wrap_use_case
from tests.feedback.feedback_setup import FeedbackSetup

APP_BASE_URL: str = "https://api.example.com"


def build_feedback_http_client(
    setup: FeedbackSetup, app_base_url: str | None = APP_BASE_URL
) -> TestClient:
    testbed = setup.testbed
    base_url = None if app_base_url is None else PublicBaseUrl(app_base_url)
    http_application = FastAPI()
    install_error_handlers(http_application)
    http_application.include_router(
        build_review_router(
            current_user=build_current_user_dependency(testbed.authentication),
            get_settings=wrap_use_case(
                GetReviewSettingsUseCase(
                    authorize_business_access=testbed.authorize_business_access,
                    review_settings_repo=setup.review_settings_repo,
                    profile_repo=testbed.profile_repo,
                    channel_repo=testbed.channel_repo,
                    text_resolver=testbed.text_resolver,
                    app_base_url=base_url,
                )
            ),
            update_settings=wrap_use_case(
                UpdateReviewSettingsUseCase(
                    authorize_business_access=testbed.authorize_business_access,
                    review_settings_repo=setup.review_settings_repo,
                    profile_repo=testbed.profile_repo,
                    channel_repo=testbed.channel_repo,
                    audit_log_repo=testbed.audit_log_repo,
                    text_resolver=testbed.text_resolver,
                    wall_clock=testbed.wall_clock,
                    app_base_url=base_url,
                )
            ),
            get_stats=wrap_use_case(
                GetReviewStatsUseCase(
                    authorize_business_access=testbed.authorize_business_access,
                    feedback_request_repo=testbed.feedback_request_repo,
                    wall_clock=testbed.wall_clock,
                )
            ),
            list_requests=wrap_use_case(
                ListFeedbackRequestsUseCase(
                    authorize_business_access=testbed.authorize_business_access,
                    feedback_request_repo=testbed.feedback_request_repo,
                    contact_repo=testbed.contact_repo,
                    audit_log_repo=testbed.audit_log_repo,
                    wall_clock=testbed.wall_clock,
                )
            ),
            open_review_link=wrap_use_case(
                OpenReviewLinkUseCase(
                    feedback_request_repo=testbed.feedback_request_repo,
                    profile_repo=testbed.profile_repo,
                    storage_scope=StorageScopeContext(),
                    wall_clock=testbed.wall_clock,
                )
            ),
        )
    )
    return TestClient(http_application, follow_redirects=False)
