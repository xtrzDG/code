"""
Records of business B for the team inbox operations of the matrix: a note
its staff member wrote (so staff may delete it) and a saved reply.
"""

from typing import Any

from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
QUICK_REPLY_BODY: JsonObject = {
    "shortcut": "hours",
    "title": "Opening hours",
    "variants": [{"language": "en", "text": "Hello {name}, we open at 9."}],
}
INBOX_BODIES: dict[str, JsonObject] = {
    # Nobody again on the unassigned newest conversation: allowed to staff.
    f"POST {B}/conversations/{{conversation_id}}/assign": {
        "assignee_user_id": None,
        "expected_revision": 0,
    },
    f"POST {B}/conversations/{{conversation_id}}/notes": {"text": "Called back"},
    f"POST {B}/quick-replies": QUICK_REPLY_BODY,
    f"PUT {B}/quick-replies/{{quick_reply_id}}": QUICK_REPLY_BODY,
}


def inbox_path_values(
    workshop: Workshop,
    business_id: str,
    conversation_id: str,
    owner_headers: dict[str, str],
    staff_headers: dict[str, str],
) -> dict[str, str]:
    """note_id (written by B's staff member) and quick_reply_id of business B."""

    client = workshop.client
    base = f"/v1/businesses/{business_id}"
    note = client.post(
        f"{base}/conversations/{conversation_id}/notes",
        json={"text": "Prefers a call after six."},
        headers=staff_headers,
    )
    assert note.status_code == 201, note.text
    reply = client.post(
        f"{base}/quick-replies",
        json={**QUICK_REPLY_BODY, "shortcut": "matrix"},
        headers=owner_headers,
    )
    assert reply.status_code == 201, reply.text
    return {"note_id": str(note.json()["id"]), "quick_reply_id": str(reply.json()["id"])}
