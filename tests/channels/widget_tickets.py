"""The stream ticket every widget answer carries, as the HTTP tests see it."""

# A signed ticket: 49 bytes in base64url without padding.
STREAM_TICKET_LENGTH: int = 66


def without_ticket(body: dict[str, object]) -> dict[str, object]:
    """
    A widget answer without its stream ticket (a fresh one each time; the
    stream tests check it), after checking that it has one.
    """

    ticket: object = body.get("stream_ticket")
    assert isinstance(ticket, str) and len(ticket) == STREAM_TICKET_LENGTH
    return {key: value for key, value in body.items() if key != "stream_ticket"}
