from starlette.middleware.cors import CORSMiddleware
from starlette.types import Receive, Scope, Send

# Public routes that answer CORS themselves for any origin: the website
# widget runs on every business's own site.
SELF_CORS_PATH_PREFIXES: tuple[str, ...] = ("/v1/widget/",)


class CabinetCorsMiddleware(CORSMiddleware):
    """
    CORS for the cabinet origins (CORS_ALLOWED_ORIGINS).

    Requests to the public widget routes pass through untouched: they allow
    any origin themselves, and the cabinet allow-list would otherwise reject
    the browser's preflight from a business's website.
    """

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and is_self_cors_path(str(scope.get("path", ""))):
            await self.app(scope, receive, send)
            return

        await super().__call__(scope, receive, send)


def is_self_cors_path(path: str) -> bool:
    return path.startswith(SELF_CORS_PATH_PREFIXES)
