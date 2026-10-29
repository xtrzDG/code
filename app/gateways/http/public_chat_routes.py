"""The hosted chat page's public configuration (no bearer token)."""

from fastapi import APIRouter, Response

from app.contracts.operator_contract import OperatorContract
from app.gateways.http.openapi_error_contract import standard_error_responses
from app.schemas.dto.sharing import HostedChatLookup, HostedChatView
from app.schemas.exceptions.application_errors import NotFoundError
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.sharing.constrained_strings import BusinessPublicSlug

PUBLIC_CHAT_PATH: str = "/v1/public/chat/{address}"
# Search engines must not list a business's chat page on the platform's
# behalf; caches may keep it briefly (the page reloads it on each visit).
PUBLIC_CHAT_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex",
}


def build_public_chat_router(
    hosted_chat_operator: OperatorContract[HostedChatLookup, HostedChatView],
) -> APIRouter:
    """
    Routes (public, no bearer token):
        GET /v1/public/chat/{address}
            what the hosted chat page needs before the widget loads: the
            business's current address (a page opened under an older one or
            under the business id moves there), name, colour, customer
            languages, whether the chat is on, the widget's script and API
            and the privacy notice. Unknown addresses are 404.
    """

    router: APIRouter = APIRouter(tags=["widget"], responses=standard_error_responses())

    @router.get(PUBLIC_CHAT_PATH)
    def get_hosted_chat(address: str, response: Response) -> HostedChatView:
        response.headers.update(PUBLIC_CHAT_HEADERS)
        return hosted_chat_operator.operate(parse_address(address))

    return router


def parse_address(raw_address: str) -> HostedChatLookup:
    """A slug, or the id of a business that has no address yet."""

    address: str = raw_address.strip()
    try:
        return HostedChatLookup(slug=BusinessPublicSlug(address))
    except ValueError:
        pass

    try:
        return HostedChatLookup(requested_business_id=BusinessId(address))
    except ValueError as error:
        raise NotFoundError("This chat is not available.") from error
