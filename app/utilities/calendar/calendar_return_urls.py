"""Where the owner lands after Google's consent page: the cabinet's Channels page."""

from urllib.parse import quote, urlencode

from app.schemas.dto.calendar import CalendarConnectionOutcome
from app.schemas.typings.bookings.constrained_strings import CalendarReturnUrl
from app.schemas.typings.platform.constrained_strings import CabinetBaseUrl

CALENDAR_QUERY_PARAMETER: str = "calendar"
REASON_QUERY_PARAMETER: str = "reason"
CONNECTED_VALUE: str = "connected"
ERROR_VALUE: str = "error"
# Without a known business (an unknown state) the owner picks one again.
BUSINESSES_PATH: str = "/businesses"
CHANNELS_PATH_TEMPLATE: str = "/b/{business_id}/channels"


def build_calendar_return_url(
    cabinet_base_url: CabinetBaseUrl,
    outcome: CalendarConnectionOutcome,
) -> CalendarReturnUrl:
    """
    {CABINET_BASE_URL}/b/{business_id}/channels?calendar=connected, or
    ?calendar=error&reason=<failure> when connecting did not finish.
    """

    path: str = (
        BUSINESSES_PATH
        if outcome.business_id is None
        else CHANNELS_PATH_TEMPLATE.format(
            business_id=quote(str(outcome.business_id), safe="")
        )
    )
    query: dict[str, str] = (
        {CALENDAR_QUERY_PARAMETER: CONNECTED_VALUE}
        if outcome.failure is None and outcome.connection is not None
        else {
            CALENDAR_QUERY_PARAMETER: ERROR_VALUE,
            REASON_QUERY_PARAMETER: (
                outcome.failure.value if outcome.failure is not None else ERROR_VALUE
            ),
        }
    )
    return CalendarReturnUrl(
        f"{str(cabinet_base_url).rstrip('/')}{path}?{urlencode(query)}"
    )
