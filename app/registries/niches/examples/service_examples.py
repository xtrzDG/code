"""
Example exchanges of the service niches: car services, home services,
education and entertainment (English, for the model).
"""

from app.registries.niches.template_parts import example
from app.schemas.constants.niches import ExampleExchangeKind as Kind
from app.schemas.dto.niches import NicheExampleExchange

CAR_SERVICE_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "An oil change for a Toyota Prius on Monday morning?",
        "[check_availability] A bay is free on Monday at <time from the tool>. "
        "Shall I book the oil change in your name? [only after a clear yes: "
        "create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much to replace a timing belt?",
        "[get_price: not found] A timing belt replacement isn't in our price "
        "list, and the final price is set after diagnostics. Shall I book a "
        "diagnostics visit or ask a mechanic to reply?",
    ),
    example(
        Kind.HANDOFF,
        "Your mechanic scratched my car door.",
        "[handoff_to_human: complaint, urgency high] I'm sorry. <what the tool "
        "returned for the customer>",
    ),
]

HOME_SERVICES_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "The kitchen tap is dripping, can someone come tomorrow to 5 Pekini Street?",
        "[check_availability] A plumber can come tomorrow at <time from the "
        "tool> to 5 Pekini Street for the dripping tap. Shall I book the visit? "
        "[only after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much to install a gas boiler?",
        "[get_price: not found] Boiler installation isn't in our price list, so "
        "I can't give an estimate. Shall I ask a specialist to reply?",
    ),
    example(
        Kind.HANDOFF,
        "I smell gas in the flat!",
        "Leave the flat and call <emergency number> now. [handoff_to_human: "
        "emergency, urgency high]",
    ),
]

EDUCATION_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Can my son try an English lesson? He is 10.",
        "[check_availability] There is a trial lesson on <day and time from the "
        "tool>. Shall I sign him up? I'll need your name and phone number. [only "
        "after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is the IELTS preparation course?",
        "[get_price: not found] IELTS preparation isn't in our price list, so I "
        "can't name a price. Shall I ask a colleague to reply?",
    ),
    example(
        Kind.HANDOFF,
        "I want a refund for the course I paid for.",
        "[handoff_to_human: non-standard request] <what the tool returned for "
        "the customer>",
    ),
]

ENTERTAINMENT_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Can we book a session for 6 people on Sunday at 3 pm?",
        "[check_availability] Sunday at 15:00 is free for 6 players. Shall I "
        "book it in your name? [only after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is a private party with a DJ?",
        "[get_price: not found] A party with a DJ isn't in our price list, so I "
        "can't name a price. Shall I take a request for a manager?",
    ),
    example(
        Kind.HANDOFF,
        "I want to talk to the manager.",
        "[handoff_to_human: customer request] <what the tool returned for the "
        "customer>",
    ),
]
