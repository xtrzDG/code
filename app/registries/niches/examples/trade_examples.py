"""
Example exchanges of the trade niches: car rental and tours, real estate,
online shops and B2B supply (English, for the model).
"""

from app.registries.niches.template_parts import example
from app.schemas.constants.niches import ExampleExchangeKind as Kind
from app.schemas.dto.niches import NicheExampleExchange

CAR_RENTAL_AND_TOURS_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "I need an SUV from 5 to 8 August.",
        "[check_availability] <car from the tool> is free from 5 to 8 August, "
        "<price from get_price>. Shall I reserve it? It is confirmed after the "
        "prepayment by the payment link. [only after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is a private tour to the mountains with a guide?",
        "[get_price: not found] That tour isn't in our price list, so I can't "
        "quote it. Shall I ask a manager to send you an offer?",
    ),
    example(
        Kind.HANDOFF,
        "The car broke down on the highway.",
        "[handoff_to_human: urgency high] I'm passing this to our team right "
        "now. <what the tool returned for the customer>",
    ),
]

REAL_ESTATE_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Can I see the two-bedroom flats on Saturday?",
        "[check_availability] A manager can show them on Saturday at <time from "
        "the tool>. Shall I book the viewing in your name? [only after a clear "
        "yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is a penthouse in the new building?",
        "[get_price: not found] A penthouse isn't in our price list, so I can't "
        "name a price. Shall I pass your request to a manager?",
    ),
    example(
        Kind.HANDOFF,
        "I'd like to discuss the payment schedule with someone.",
        "[handoff_to_human: customer request] <what the tool returned for the "
        "customer>",
    ),
]

ONLINE_SHOP_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.REQUEST_CONFIRMATION,
        "The black hoodie in size M, two pieces, to 12 Rustaveli Avenue.",
        "The black hoodie, size M, 2 pieces, delivery to 12 Rustaveli Avenue: "
        "shall I send this order to a manager? They confirm stock, delivery and "
        "payment. [only after a clear yes: create_lead]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is delivery to Batumi?",
        "[search_knowledge: nothing found] I don't have the delivery price to "
        "Batumi. A manager tells you when they confirm the order; shall I pass "
        "the question on?",
    ),
    example(
        Kind.HANDOFF,
        "I received the wrong size.",
        "[handoff_to_human: complaint, urgency high] I'm sorry about that. <what "
        "the tool returned for the customer>",
    ),
]

B2B_SUPPLY_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.REQUEST_CONFIRMATION,
        "We need 200 kg of flour every week for our bakery in Rustavi, starting "
        "next month.",
        "Thank you! What is your company name? Then I'll pass the order to a "
        "manager: flour, 200 kg a week, delivery to Rustavi, from next month. "
        "The manager sends the exact offer. [only after a clear yes: create_lead]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "Do you sell coconut oil, and at what price?",
        "[get_price: not found] Coconut oil isn't in our price list, so I can't "
        "quote it. Shall I ask a manager to reply?",
    ),
    example(
        Kind.HANDOFF,
        "Our last delivery came two days late.",
        "[handoff_to_human: complaint, urgency high] I'm sorry. <what the tool "
        "returned for the customer>",
    ),
]
