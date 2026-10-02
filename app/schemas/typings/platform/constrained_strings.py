"""Keep abc order."""

from base_typed_string import BaseConstrainedTypedString


class CabinetBaseUrl(BaseConstrainedTypedString):
    """
    Public address of the owner cabinet (the web app), where the backend
    sends owners back after a provider's consent page.

    Example:
        cabinet_url = CabinetBaseUrl("https://app.example.com")
    """

    min_length = 10
    max_length = 2048
    pattern = r"^https?://[^\s/?#]+(/[^\s?#]*)?$"


class EnvironmentVariableName(BaseConstrainedTypedString):
    """
    Name of a server setting read from the environment, e.g. "APP_BASE_URL";
    reported when a feature cannot work because the setting is missing.

    Example:
        name = EnvironmentVariableName("ELEVENLABS_API_KEY")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Z][A-Z0-9_]*$"


class ErrorReasonCode(BaseConstrainedTypedString):
    """
    Stable machine-readable code of one reason an API request was refused,
    e.g. "dpa" or "menu_link_unreachable"; clients branch on it instead of
    the English message.

    Example:
        code = ErrorReasonCode("profile_gaps")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class ErrorReasonDetail(BaseConstrainedTypedString):
    """
    One machine value that qualifies a refusal reason: a gap kind, a status,
    a document version, the name of a missing setting or a media type.

    Example:
        detail = ErrorReasonDetail("no_opening_hours")
    """

    min_length = 1
    max_length = 120
    pattern = r"^[A-Za-z0-9][A-Za-z0-9_.:/+\-]*$"


class JobLeaseToken(BaseConstrainedTypedString):
    """
    Random token of one claim of queued jobs by a worker. Only the worker
    holding the token may extend the lease or settle the job, so a worker
    whose lease expired cannot overwrite the result of the next attempt.

    Example:
        token = JobLeaseToken("4f6c1e2a9b3d4c5e8f7a6b5c4d3e2f1a")
    """

    min_length = 32
    max_length = 32
    pattern = r"^[0-9a-f]{32}$"


class JobName(BaseConstrainedTypedString):
    """
    Stable snake-case name of a background job, e.g. "purge_expired_recordings".

    Example:
        name = JobName("send_booking_reminders")
    """

    min_length = 2
    max_length = 64
    pattern = r"^[a-z][a-z0-9_]*$"


class JobPeriodKey(BaseConstrainedTypedString):
    """
    The period one run of a periodic job belongs to, in UTC: the date of a
    daily job ("2026-10-02"), the ISO week of a weekly job ("2026-W40"), or
    the start of the interval of a shorter one ("2026-10-02T14:15:00Z"). A
    job runs once per period across workers and restarts.

    Example:
        period = JobPeriodKey("2026-10-02")
    """

    min_length = 8
    max_length = 20
    pattern = r"^\d{4}-(W\d{2}|\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?)$"


class JobSerialKey(BaseConstrainedTypedString):
    """
    Key of queued jobs that must run one at a time, oldest first (e.g. the
    autotest runs of one business, or the messages of one customer): a
    worker never starts a job while another job with the same key runs.

    Example:
        key = JobSerialKey("autotests:business_0f8f6bd6e9b24a4c8b8c3c1f2a7e9d10")
    """

    min_length = 3
    max_length = 200
    pattern = r"^[a-z][a-z0-9_]*:[A-Za-z0-9_.:\-]+$"


class PageCursor(BaseConstrainedTypedString):
    """
    Opaque position in a list sorted newest first, returned as `next_cursor`
    and sent back as `cursor` to get the next page.

    Example:
        cursor = PageCursor("MTc5MDg2MTAwODg1MzAwMDpib29raW5nXzE")
    """

    min_length = 1
    max_length = 200
    pattern = r"^[A-Za-z0-9_-]+$"


class RateLimitKey(BaseConstrainedTypedString):
    """
    What one rate-limit counter counts: the kind of request and who or what
    makes it ("widget-message:business:biz_..."). Every API instance counts
    the same key in the same shared counter.

    Example:
        key = RateLimitKey("otp-check:address:203.0.113.7")
    """

    min_length = 1
    max_length = 400


class ReleaseVersion(BaseConstrainedTypedString):
    """
    The deployed build of the backend: the git commit Render builds from
    (RENDER_GIT_COMMIT) or a version name. Error reports and worker
    heartbeats name it, so a fault can be traced to one deploy.

    Example:
        release = ReleaseVersion("4718714c0f2e9a1b7d3c5e6f8a9b0c1d2e3f4a5b")
    """

    min_length = 1
    max_length = 64
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$"


class RequestId(BaseConstrainedTypedString):
    """
    The X-Request-ID of one HTTP request: taken from the caller when it is
    short printable ASCII, otherwise generated. Every log line and error
    report of the request carries it, and the response echoes it.

    Example:
        request_id = RequestId("0b7c3f0e-58f1-4c44-9a63-2f1f9f0c1b2a")
    """

    min_length = 1
    max_length = 128
    pattern = r"^[\x20-\x7e]+$"


class WorkerHostName(BaseConstrainedTypedString):
    """
    Host name of the machine or container a background worker process runs
    on, as its heartbeat reports it (no personal data).

    Example:
        host = WorkerHostName("srv-d1f2g3h4-5b6c7")
    """

    min_length = 1
    max_length = 255
    pattern = r"^[A-Za-z0-9][A-Za-z0-9._\-]*$"


# Keep abc order for all non example types, if possible.
