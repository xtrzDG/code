"""
Records of business B for the teaching operations of the matrix: an
assistant answer of the conversation the matrix uses (to correct) and one
of the owner's own checks.
"""

from typing import Any, cast

from tests.e2e.harness import Workshop

type JsonObject = dict[str, Any]

B: str = "/v1/businesses/{business_id}"
CASE_BODY: JsonObject = {
    "question": "Do you have a terrace?",
    "expectation": "must_mention",
    "expected_text": "terrace",
}
TEACHING_BODIES: dict[str, JsonObject] = {
    f"POST {B}/conversations/{{conversation_id}}/messages/{{message_id}}/correction": {
        "scope": "faq",
        "question": "Is there a terrace?",
        "correct_answer": "Yes, a terrace with twelve tables.",
    },
    f"POST {B}/autotest-cases": {**CASE_BODY, "question": "Is the terrace open?"},
}


def teaching_path_values(
    workshop: Workshop,
    business_id: str,
    conversation_id: str,
    owner_headers: dict[str, str],
) -> dict[str, str]:
    """message_id (an assistant answer) and case_id (a check) of business B."""

    client = workshop.client
    base = f"/v1/businesses/{business_id}"
    transcript = client.get(
        f"{base}/conversations/{conversation_id}/messages?limit=100",
        headers=owner_headers,
    ).json()
    messages = cast(list[JsonObject], transcript["items"])
    answer = next(message for message in messages if message["author"] == "assistant")
    case = client.post(f"{base}/autotest-cases", json=CASE_BODY, headers=owner_headers)
    assert case.status_code == 201, case.text
    return {"message_id": str(answer["id"]), "case_id": str(case.json()["id"])}
