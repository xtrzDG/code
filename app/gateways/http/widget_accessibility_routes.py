"""
The website chat's link to the platform's accessibility statement: the
widget knows the API, not the public site, so the API sends the browser
on to `{CABINET_BASE_URL}/{locale}/accessibility` in the locale of the
visitor's language the site has (English otherwise).
"""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse

from app.gateways.http.openapi_error_contract import standard_error_responses
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

WIDGET_ACCESSIBILITY_PATH: str = "/widget/accessibility"
# The public site's locales (web/src/i18n/config.ts LOCALES); the first is
# its fallback.
PUBLIC_SITE_LOCALES: tuple[str, ...] = ("en", "it")
# The statement's path in each locale: the redirect only ever takes one of
# these constants, never text from the request.
STATEMENT_PATHS: dict[str, str] = {
    locale: f"/{locale}/accessibility" for locale in PUBLIC_SITE_LOCALES
}
# The address only changes with a release: browsers keep it for a day.
REDIRECT_CACHE_CONTROL: str = "public, max-age=86400"
MAX_LANGUAGE_LENGTH: int = 35


def public_site_locale(language: str | None) -> str:
    """The site's locale of a language tag ("it-IT" -> "it", "fr" -> "en")."""

    if language is None or len(language) > MAX_LANGUAGE_LENGTH:
        return PUBLIC_SITE_LOCALES[0]

    base: str = language.strip().replace("_", "-").split("-")[0].lower()
    return base if base in PUBLIC_SITE_LOCALES else PUBLIC_SITE_LOCALES[0]


def build_widget_accessibility_router(
    public_site_base_url: CabinetBaseUrl | None,
) -> APIRouter:
    """
    Route (no token, not in the API description):
        GET /widget/accessibility?language=<tag>   302 to the statement;
                                                   404 without CABINET_BASE_URL
    """

    router = APIRouter(responses=standard_error_responses())

    @router.get(WIDGET_ACCESSIBILITY_PATH, include_in_schema=False)
    def open_accessibility_statement(
        language: Annotated[str | None, Query()] = None,
    ) -> RedirectResponse:
        if public_site_base_url is None:
            raise NotFoundError("The public site is not configured here.")

        site: str = str(public_site_base_url).rstrip("/")
        statement: str = STATEMENT_PATHS.get(
            public_site_locale(language), STATEMENT_PATHS[PUBLIC_SITE_LOCALES[0]]
        )
        return RedirectResponse(
            f"{site}{statement}",
            status_code=302,
            headers={"Cache-Control": REDIRECT_CACHE_CONTROL},
        )

    return router
