"""
The one request to rewrite a reply the guard held back: the values the
evidence does not back, the policy or availability statements it does not
back, a booking said to be done that no booking tool made, contact details
that are neither the business's nor the customer's own, links the business
did not publish, and the quote of a team note.
"""

from collections.abc import Sequence

from app.utilities.conversations.turn_context import build_rewrite_note

PLATFORM_CHECK_HEADER: str = "[Check by the platform, not written by the customer]"


def build_guard_rewrite_note(
    unverified_values: list[str],
    unsupported_claims: list[str],
    withheld_details: list[str],
    foreign_links: Sequence[str] = (),
    quotes_team_note: bool = False,
    booking_claims: Sequence[str] = (),
) -> str:
    """The note; a reply held back for its values alone keeps the old wording."""

    if (
        not unsupported_claims
        and not withheld_details
        and not foreign_links
        and not quotes_team_note
        and not booking_claims
    ):
        return build_rewrite_note(unverified_values)

    lines: list[str] = [PLATFORM_CHECK_HEADER]
    if unverified_values:
        lines.append(
            "Your last reply mentions values that are not in the fact table, "
            "the tool results or the customer's messages: "
            + "; ".join(unverified_values)
            + "."
        )

    if unsupported_claims:
        lines.append(
            "The facts and tool results do not back these statements of your "
            "last reply: " + " | ".join(unsupported_claims)
        )

    if booking_claims:
        lines.append(
            "No booking tool succeeded in this turn, yet your last reply says a "
            "booking is made, confirmed, moved or cancelled: "
            + " | ".join(booking_claims)
            + " Say so only after create_booking, reschedule_booking or "
            "cancel_booking succeeded (or list_my_bookings shows it)."
        )

    if withheld_details:
        lines.append(
            "Your last reply contains contact details that are neither the "
            "business's nor this customer's own: "
            + "; ".join(withheld_details)
            + ". Never share another person's phone number or e-mail address."
        )

    if foreign_links:
        lines.append(
            "Your last reply contains links the business did not publish: "
            + "; ".join(foreign_links)
            + ". Use only links from the facts or tool results (send_link)."
        )

    if quotes_team_note:
        lines.append(
            "Your last reply quotes an internal note of the business's team. "
            "Use the team's notes only as background and never repeat them to "
            "the customer."
        )

    lines.append(
        "Write the reply again in the customer's language without them: say "
        "only what the facts and tool results say, call a tool to check, or "
        "offer to pass the question to a colleague."
    )
    return "\n".join(lines)
