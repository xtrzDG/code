"""
A hook of ZAP's packaged API scan (.github/workflows/zap.yml, `--hook`):
before ZAP shuts down it writes the address and the HTTP status of every
answer the scan received to a JSON file of the scans' folder, so that
scripts/zap_auth_check.py can prove the /v1 scan was signed in. ZAP's
reports list findings only; without this a scan whose bearer header was
never sent would pass on 401 answers alone.

ZAP loads this file by its path inside its own container (Python 3 with
ZAP's API client): it imports nothing but the standard library.
"""

import json
import os
from collections.abc import Iterator
from typing import Any

# ZAP calls the hook by this name; nothing in this repository does.
__all__ = ["zap_pre_shutdown"]

STATUS_FILE_VARIABLE: str = "ZAP_STATUS_FILE"
DEFAULT_STATUS_FILE: str = "/zap/wrk/api-statuses.json"
PAGE_SIZE: int = 500


def request_url(request_header: str) -> str:
    """The address of `GET http://host/path HTTP/1.1`."""

    parts = request_header.split(" ", 2)
    return parts[1] if len(parts) > 1 else ""


def response_status(response_header: str) -> int:
    """The status of `HTTP/1.1 200 OK`; 0 when ZAP received no answer."""

    parts = response_header.split(" ", 2)
    if len(parts) > 1 and parts[1].isdigit():
        return int(parts[1])
    return 0


def answers(zap: Any) -> Iterator[dict[str, Any]]:
    start = 0
    while True:
        page: list[dict[str, Any]] = zap.core.messages(
            start=str(start), count=str(PAGE_SIZE)
        )
        for message in page:
            yield {
                "url": request_url(str(message.get("requestHeader", ""))),
                "status": response_status(str(message.get("responseHeader", ""))),
            }
        if len(page) < PAGE_SIZE:
            return
        start += PAGE_SIZE


def zap_pre_shutdown(zap: Any) -> None:
    """ZAP's hook: called once the scan finished, before ZAP stops."""

    path = os.environ.get(STATUS_FILE_VARIABLE, DEFAULT_STATUS_FILE)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(list(answers(zap)), file)
