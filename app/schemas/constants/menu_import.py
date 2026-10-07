from enum import StrEnum


class MenuLinkProblem(StrEnum):
    """
    Why a menu link could not be read: `reasons[].code` of the 422 answer
    to a link import (an unavailable menu model stays a 502
    external_service_error).

    - menu_link_invalid: not an http(s) address of a public host on port
      80 or 443 (details: "not_http", "credentials_in_url",
      "port_not_allowed" or "not_public");
    - menu_link_unreachable: the page could not be fetched (details:
      "unknown_host", "timeout", "connection_failed", "request_failed",
      "http_status:<code>", "redirect_without_location",
      "too_many_redirects");
    - menu_link_unreadable: the page was fetched but cannot be read as a
      menu (details: "too_large", "media_type:<type>" or
      "content_encoding:<encoding>").
    """

    INVALID = "menu_link_invalid"
    UNREACHABLE = "menu_link_unreachable"
    UNREADABLE = "menu_link_unreadable"
