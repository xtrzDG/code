"""Who may read a metrics page: a scraper with the bearer METRICS_TOKEN."""

import hmac

from app.schemas.typings.platform.strings import PlatformSecret

BEARER_PREFIX: str = "Bearer "


def carries_metrics_token(authorization: str | None, token: PlatformSecret) -> bool:
    """Whether the Authorization header carries the token (constant time)."""

    if authorization is None or not authorization.startswith(BEARER_PREFIX):
        return False

    offered: str = authorization.removeprefix(BEARER_PREFIX).strip()
    return hmac.compare_digest(offered.encode(), str(token).encode())
