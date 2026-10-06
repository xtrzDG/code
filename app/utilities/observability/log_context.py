"""
The log context: which request, business, conversation and job the current
code works for, so every log line and error report can be traced to them.

It lives in a context variable: the request middleware binds the request
id and its trace id, `BusinessScopedPipelineOperator` the business, the
conversation turn its conversation, contact and channel, the background
worker the job (with the request id and trace of what queued it).
Bindings nest and are undone on exit; asyncio tasks and the request
threads of AnyIO (`to_thread.run_sync` copies the context) inherit them, a
new `threading.Thread` starts empty.

An error that leaves a bound block is stamped with the context it came
from (the innermost one), so the handler that reports it outside every
block (the HTTP 500 handler) still knows the request and the business.
"""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token

from app.schemas.constants.channels import ChannelKind
from app.schemas.dto.observability import LogContext
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.contacts.prefixed_id import ContactId
from app.schemas.typings.conversations.prefixed_id import ConversationId
from app.schemas.typings.observability.constrained_strings import TraceId
from app.schemas.typings.platform.constrained_strings import JobName, RequestId
from app.schemas.typings.platform.prefixed_id import QueuedJobId

EMPTY_LOG_CONTEXT: LogContext = LogContext()
# Attribute of an exception that carries the context it was raised in.
ERROR_CONTEXT_ATTRIBUTE: str = "__workshop_log_context__"

_current_log_context: ContextVar[LogContext] = ContextVar(
    "log_context",
    default=EMPTY_LOG_CONTEXT,
)


def current_log_context() -> LogContext:
    """The context of the code running now (empty outside any binding)."""

    return _current_log_context.get()


@contextmanager
def bound_log_context(
    *,
    request_id: RequestId | None = None,
    trace_id: TraceId | None = None,
    business_id: BusinessId | None = None,
    conversation_id: ConversationId | None = None,
    contact_id: ContactId | None = None,
    channel: ChannelKind | None = None,
    job_name: JobName | None = None,
    job_id: QueuedJobId | None = None,
) -> Generator[LogContext]:
    """
    Add the given values to the current context for the block (values left
    out, or None, keep what the outer context had).
    """

    changes: dict[str, object] = {
        name: value
        for name, value in (
            ("request_id", request_id),
            ("trace_id", trace_id),
            ("business_id", business_id),
            ("conversation_id", conversation_id),
            ("contact_id", contact_id),
            ("channel", channel),
            ("job_name", job_name),
            ("job_id", job_id),
        )
        if value is not None
    }
    context: LogContext = current_log_context().model_copy(update=changes)
    with restored_log_context(context):
        yield context


@contextmanager
def restored_log_context(context: LogContext) -> Generator[LogContext]:
    """Make exactly `context` current for the block (e.g. an error's context)."""

    token: Token[LogContext] = _current_log_context.set(context)
    try:
        yield context
    except BaseException as error:
        stamp_error_context(error, context)
        raise
    finally:
        _current_log_context.reset(token)


def stamp_error_context(error: BaseException, context: LogContext) -> None:
    """Remember where `error` came from, unless an inner block already did."""

    if getattr(error, ERROR_CONTEXT_ATTRIBUTE, None) is not None:
        return

    try:
        setattr(error, ERROR_CONTEXT_ATTRIBUTE, context)
    except AttributeError:  # an exception type with __slots__
        return


def log_context_of_error(error: BaseException) -> LogContext:
    """The context `error` was raised in, else the current one."""

    stamped: object = getattr(error, ERROR_CONTEXT_ATTRIBUTE, None)
    if isinstance(stamped, LogContext):
        return stamped

    return current_log_context()
