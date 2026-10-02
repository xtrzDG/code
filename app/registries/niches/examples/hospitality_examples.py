"""
Example exchanges of the hospitality niches: restaurants, hotels, short-term
rentals and event venues (English, for the model).
"""

from app.registries.niches.template_parts import example
from app.schemas.constants.niches import ExampleExchangeKind as Kind
from app.schemas.dto.niches import NicheExampleExchange

RESTAURANT_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "A table for four this Saturday at 8 pm, please. I'm Nino.",
        "[check_availability] A table for 4 is free on Saturday <date> at 20:00. "
        "Shall I book it for Nino? [only after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is the lobster platter?",
        "[get_price: not found] I can't find a lobster platter in our menu, so I "
        "can't name a price. Shall I pass your question to a colleague?",
    ),
    example(
        Kind.HANDOFF,
        "The soup was cold yesterday and nobody even apologised.",
        "[handoff_to_human: complaint, urgency high] I'm sorry about that. "
        "<what the tool returned for the customer>",
    ),
]

HOTEL_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Do you have a double room from 12 March for 3 nights, 2 adults?",
        "[check_availability] A <room type> is free for 3 nights from 12 March "
        "for 2 guests, <price from get_price>. Shall I book it in your name? "
        "[only after a clear yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is an airport pickup?",
        "[get_price: not found] An airport pickup isn't in our price list, so I "
        "can't quote it. Shall I ask a colleague to reply?",
    ),
    example(
        Kind.HANDOFF,
        "My key card doesn't work and I'm standing at the door.",
        "[handoff_to_human: urgency high] I'm passing this to the staff right "
        "away. <what the tool returned for the customer>",
    ),
]

SHORT_TERM_RENTAL_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Is the apartment free from Friday for 2 nights? We are 3.",
        "[check_availability] Yes, it is free for 2 nights from Friday <date> "
        "for 3 guests. Shall I book it in your name? [only after a clear yes: "
        "create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much do you charge for an early check-in?",
        "[search_knowledge: nothing found] I don't have a price for an early "
        "check-in. Shall I ask the host?",
    ),
    example(
        Kind.HANDOFF,
        "The door code doesn't work, I'm outside with my bags.",
        "[handoff_to_human: urgency high] I'm alerting the host right now. "
        "<what the tool returned for the customer> (Never share door or lock-box "
        "codes yourself.)",
    ),
]

EVENT_VENUE_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.REQUEST_CONFIRMATION,
        "We are planning a wedding for 120 guests on 14 June, budget about 15,000.",
        "Thank you! I'll pass your request to a manager: a wedding, 120 guests, "
        "14 June, budget as you said. The manager confirms the date and the "
        "menu. Shall I send it? [only after a clear yes: create_lead]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much do you charge for fireworks?",
        "[get_price: not found] Fireworks aren't in our price list, so I can't "
        "name a price. A manager can answer that with your event request.",
    ),
    example(
        Kind.HANDOFF,
        "Can I talk to the manager about the menu tasting?",
        "[handoff_to_human: customer request] <what the tool returned for the "
        "customer>",
    ),
]
