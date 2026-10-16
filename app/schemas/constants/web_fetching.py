from enum import StrEnum


class WebFetchProblem(StrEnum):
    """
    Why the safe fetcher did not return a resource. The first group means
    the address must not be fetched at all (it is refused before any
    connection), the second that it could not be fetched, the third that
    what came back cannot be used.
    """

    # Refused: the address is not a public http(s) address on port 80/443.
    NOT_HTTP = "not_http"
    CREDENTIALS_IN_URL = "credentials_in_url"
    PORT_NOT_ALLOWED = "port_not_allowed"
    NOT_PUBLIC = "not_public"
    # Not fetched: the host or the server failed.
    UNKNOWN_HOST = "unknown_host"
    TIMEOUT = "timeout"
    CONNECTION_FAILED = "connection_failed"
    REQUEST_FAILED = "request_failed"
    HTTP_STATUS = "http_status"
    REDIRECT_WITHOUT_LOCATION = "redirect_without_location"
    TOO_MANY_REDIRECTS = "too_many_redirects"
    # Fetched, but unusable.
    TOO_LARGE = "too_large"
    UNSUPPORTED_MEDIA_TYPE = "media_type"
    UNSUPPORTED_ENCODING = "content_encoding"


REFUSED_FETCH_PROBLEMS: frozenset[WebFetchProblem] = frozenset(
    {
        WebFetchProblem.NOT_HTTP,
        WebFetchProblem.CREDENTIALS_IN_URL,
        WebFetchProblem.PORT_NOT_ALLOWED,
        WebFetchProblem.NOT_PUBLIC,
    }
)
UNUSABLE_FETCH_PROBLEMS: frozenset[WebFetchProblem] = frozenset(
    {
        WebFetchProblem.TOO_LARGE,
        WebFetchProblem.UNSUPPORTED_MEDIA_TYPE,
        WebFetchProblem.UNSUPPORTED_ENCODING,
    }
)
