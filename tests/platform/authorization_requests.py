"""
The operations of the authorization matrix, read from the API description:
every operation under /v1/businesses/{business_id}, with its path filled
from business B's records, a minimal valid body and its required query.
A new operation joins the matrix by itself; one that needs a body or a
query value the tables below do not have fails until it is added.
"""

import re
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from tests.platform.authorization_notifications import NOTIFICATION_BODIES

type JsonObject = dict[str, Any]

BUSINESS_PREFIX: str = "/v1/businesses/{business_id}"
PATH_PARAMETER: re.Pattern[str] = re.compile(r"\{([a-z_]+)\}")
HTTP_METHODS: tuple[str, ...] = ("get", "post", "put", "patch", "delete")
B: str = BUSINESS_PREFIX
# Minimal valid bodies of operations whose body has required fields (all
# others are sent `{}`): the refusal must not depend on a malformed body.
REQUEST_BODIES: dict[str, JsonObject] = {
    f"POST {B}/billing/plan": {"plan_key": "chat", "billing_period": "monthly"},
    f"POST {B}/billing/subscribe": {"plan_key": "chat"},
    f"POST {B}/bookings": {
        "contact_name": "Nino",
        "date": "2026-10-20",
        "party_size": 2,
    },
    f"POST {B}/bookings/{{booking_id}}/reschedule": {"new_date": "2026-10-21"},
    f"PUT {B}/channels/whatsapp/staff-template": {
        "name": "staff_reply",
        "language_code": "en",
    },
    f"PUT {B}/channels/{{channel}}": {
        "bot_token": "123456789:AAMatrixBusinessBotTokenForTheTest0123"
    },
    f"POST {B}/conversations/{{conversation_id}}/messages": {"text": "Hello"},
    f"PUT {B}/conversations/{{conversation_id}}/rating": {"rating": "good"},
    f"POST {B}/knowledge": {"kind": "faq", "title": "Parking"},
    f"POST {B}/knowledge/import": {"media_type": "text/plain", "data_base64": "VGVh"},
    f"POST {B}/knowledge/import/confirm": {"item_ids": []},
    f"POST {B}/knowledge/search": {"query": "tea"},
    f"PATCH {B}/leads/{{lead_id}}": {"status": "in_progress"},
    f"POST {B}/manager-contacts/telegram-link": {"name": "Nino"},
    f"POST {B}/members": {"phone_number": "+995 555 77 88 99", "role": "staff"},
    f"PATCH {B}/members/{{user_id}}": {"role": "staff"},
    f"POST {B}/resources": {"name": "Terrace", "capacity": 4},
    f"POST {B}/schedule-exceptions": {"date": "2026-12-31", "is_closed_all_day": True},
    f"POST {B}/test-chat": {"text": "Hello"},
    f"POST {B}/unanswered-questions/{{question_id}}/answer": {
        "answer": "Yes, dogs are welcome on the terrace."
    },
}
REQUEST_BODIES.update(NOTIFICATION_BODIES)
REQUIRED_QUERIES: dict[str, dict[str, str]] = {
    f"GET {B}/availability": {"date": "2026-10-20"},
}


@dataclass(frozen=True)
class MatrixOperation:
    """One business operation as the API description names it."""

    method: str
    path: str
    has_body: bool

    @property
    def key(self) -> str:
        return f"{self.method.upper()} {self.path}"


def business_operations(application: FastAPI) -> list[MatrixOperation]:
    """Every documented operation under /v1/businesses/{business_id}."""

    paths = cast(dict[str, JsonObject], application.openapi()["paths"])
    operations: list[MatrixOperation] = []
    for path, path_item in sorted(paths.items()):
        if not path.startswith(BUSINESS_PREFIX):
            continue

        for method in HTTP_METHODS:
            operation: JsonObject | None = path_item.get(method)
            if operation is None:
                continue

            operations.append(
                MatrixOperation(
                    method=method,
                    path=path,
                    has_body="requestBody" in operation,
                )
            )

    return operations


def fill_path(operation: MatrixOperation, values: dict[str, str]) -> str:
    """The operation's path with each parameter taken from `values`."""

    missing: list[str] = [
        name for name in PATH_PARAMETER.findall(operation.path) if name not in values
    ]
    assert missing == [], (
        f"{operation.key}: add a record of business B for {missing} to "
        "tests/platform/authorization_world.py"
    )
    return PATH_PARAMETER.sub(lambda match: values[match.group(1)], operation.path)


def request_body(operation: MatrixOperation) -> JsonObject | None:
    """The table's body, `{}` for a body without required fields, or none."""

    if not operation.has_body:
        return None

    return REQUEST_BODIES.get(operation.key, {})


def call_operation(
    client: TestClient,
    operation: MatrixOperation,
    values: dict[str, str],
    headers: dict[str, str],
) -> Response:
    """Send the operation with B's ids, a valid body and its query."""

    return client.request(
        operation.method.upper(),
        fill_path(operation, values),
        params=REQUIRED_QUERIES.get(operation.key),
        json=request_body(operation),
        headers=headers,
    )
