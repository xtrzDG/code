"""The website widget's error beacon: POST /v1/widget/errors."""

from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.observability import WidgetErrorKind, WidgetErrorPhase
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_integers import (
    WidgetConfigStatusCode,
    WidgetScriptPosition,
)
from app.schemas.typings.channels.constrained_strings import WidgetErrorName
from app.schemas.typings.compliance.strings import ClientIpAddress


class WidgetErrorReport(ImmutableDTO):
    """
    HTTP body of one widget error: what failed and where in widget.js. No
    message text, page address or visitor data: an error message may quote
    the business's page or what the visitor typed.
    """

    kind: WidgetErrorKind
    phase: WidgetErrorPhase
    business_id: BusinessId | None = None
    error_name: WidgetErrorName | None = None
    line: WidgetScriptPosition | None = None
    column: WidgetScriptPosition | None = None
    status_code: WidgetConfigStatusCode | None = None


class WidgetErrorCommand(ImmutableDTO):
    """A widget error report and the client network it came from."""

    report: WidgetErrorReport
    client_ip_address: ClientIpAddress | None = None
