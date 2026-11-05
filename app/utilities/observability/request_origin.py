"""
Where the HTTP request being served comes from, for the records that must
name it (LOG-01): the client address and User-Agent, bound by the request
middleware, and the person the request acts for, noted once its bearer
token is checked.

Audit entries take the request id, and for a person's own action the
address and User-Agent, from here when their use case named none
(`stamp_audit_origin`); security log lines name the actor
(`current_security_actor`). Not part of the log context: an ordinary log
line never carries an address or a User-Agent.

The origin is one mutable holder per request, so the actor noted inside
an async dependency is seen by the error handlers and middlewares around
it; a job, a new thread or another request starts with none.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from app.schemas.typings.compliance.constrained_strings import AuditUserAgent
from app.schemas.typings.compliance.strings import ClientIpAddress
from app.schemas.typings.users.constrained_strings import SessionUserAgent
from app.schemas.typings.users.prefixed_id import UserId
from app.utilities.security.user_agents import read_user_agent

# The actor of a security line: a request nobody signed in to, or work
# outside any request (a job, a startup check).
ANONYMOUS_ACTOR: str = "anonymous"
SYSTEM_ACTOR: str = "system"


class RequestOrigin:
    """The client of one request and, once known, the person it acts for."""

    __slots__ = ("actor_id", "client_ip_address", "user_agent")

    def __init__(
        self,
        client_ip_address: ClientIpAddress | None,
        user_agent: AuditUserAgent | None,
    ) -> None:
        self.client_ip_address: ClientIpAddress | None = client_ip_address
        self.user_agent: AuditUserAgent | None = user_agent
        self.actor_id: UserId | None = None


_current_origin: ContextVar[RequestOrigin | None] = ContextVar(
    "request_origin", default=None
)


@contextmanager
def bound_request_origin(
    client_address: str | None,
    raw_user_agent: str | None,
) -> Generator[RequestOrigin]:
    """The origin of the request served inside the block (raw transport values)."""

    origin = RequestOrigin(
        client_ip_address=(
            None if not client_address else ClientIpAddress(client_address)
        ),
        user_agent=read_audit_user_agent(raw_user_agent),
    )
    token: Token[RequestOrigin | None] = _current_origin.set(origin)
    try:
        yield origin
    finally:
        _current_origin.reset(token)


def current_request_origin() -> RequestOrigin | None:
    """The origin of the request being served; None outside a request."""

    return _current_origin.get()


def note_request_actor(actor_id: UserId) -> None:
    """Remember who the request acts for (its bearer token was accepted)."""

    origin: RequestOrigin | None = _current_origin.get()
    if origin is not None:
        origin.actor_id = actor_id


def current_security_actor() -> str:
    """
    Who a security line is about: the signed-in person's id (a pseudonym,
    never a name or an address), `anonymous` for a request without one,
    `system` outside any request.
    """

    origin: RequestOrigin | None = _current_origin.get()
    if origin is None:
        return SYSTEM_ACTOR

    return ANONYMOUS_ACTOR if origin.actor_id is None else str(origin.actor_id)


def read_audit_user_agent(raw_value: str | None) -> AuditUserAgent | None:
    """
    The User-Agent header as an audit entry keeps it: cleaned as a
    session's (printable ASCII only, so no line breaks, cut to 512
    characters); None when nothing is left.
    """

    cleaned: SessionUserAgent | None = read_user_agent(raw_value)
    return None if cleaned is None else AuditUserAgent(str(cleaned))
