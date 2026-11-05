"""The stream ticket a widget answer carries (see `WidgetStreamTicketSigner`)."""

from typed_time_provider import Microseconds

from app.contracts.widget_streams import WidgetStreamTicketSignerContract
from app.schemas.dto.channels.widget_streams import WidgetStreamClaims
from app.schemas.typings.businesses.prefixed_id import BusinessId
from app.schemas.typings.channels.constrained_strings import WidgetStreamTicket
from app.utilities.channels.widget_visitors import widget_visitor_id

# A ticket opens the visitor's stream for an hour: its reconnects (every
# stream ends after 15 minutes) reuse it; after that the widget's next
# answer or poll brings a fresh one.
STREAM_TICKET_SECONDS: int = 60 * 60
MICROSECONDS_PER_SECOND: int = 1_000_000


def issue_stream_ticket(
    signer: WidgetStreamTicketSignerContract,
    business_id: BusinessId,
    visitor_key: str,
    now: Microseconds,
) -> WidgetStreamTicket:
    """A ticket to the stream of the visitor whose key the request carried."""

    return signer.sign(
        WidgetStreamClaims(
            business_id=business_id,
            visitor_id=widget_visitor_id(visitor_key),
            expires_at=Microseconds(
                int(now) + STREAM_TICKET_SECONDS * MICROSECONDS_PER_SECOND
            ),
        )
    )
