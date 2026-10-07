from typed_time_provider import Microseconds, WallClock

from app.contracts.observability import ClientErrorReportingFacilitatorContract
from app.contracts.registries import RequestRateLimitRegistryContract
from app.contracts.use_case_contract import UseCaseContract
from app.schemas.dto.widget_errors import WidgetErrorCommand
from app.utilities.channels.widget_error_limits import refuse_too_many_error_reports


class ReportWidgetErrorUseCase(UseCaseContract[WidgetErrorCommand, None]):
    """
    An error of the website widget on a business's site, reported by its
    error beacon: limited per client network, business and platform
    (`widget_error_limits`), then logged and sent to the error reporter
    (Sentry) with what failed and where in widget.js. The report holds no
    message text or visitor data, and the business named in it is not
    looked up: an unknown one is reported as it came.
    """

    def __init__(
        self,
        client_error_reporter: ClientErrorReportingFacilitatorContract,
        rate_limit_registry: RequestRateLimitRegistryContract,
        wall_clock: WallClock[Microseconds],
    ) -> None:
        self._client_error_reporter: ClientErrorReportingFacilitatorContract = (
            client_error_reporter
        )
        self._rate_limit_registry: RequestRateLimitRegistryContract = (
            rate_limit_registry
        )
        self._wall_clock: WallClock[Microseconds] = wall_clock

    def run(self, input_data: WidgetErrorCommand) -> None:
        refuse_too_many_error_reports(
            self._rate_limit_registry,
            business_id=input_data.report.business_id,
            client_ip_address=input_data.client_ip_address,
            now=self._wall_clock.now_unix(),
        )
        self._client_error_reporter.capture_widget_error(input_data.report)
