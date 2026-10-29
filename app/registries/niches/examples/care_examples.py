"""
Example exchanges of the care niches: beauty salons, clinics, veterinary
clinics and fitness clubs (English, for the model).
"""

from app.registries.niches.template_parts import example
from app.schemas.constants.niches import ExampleExchangeKind as Kind
from app.schemas.dto.niches import NicheExampleExchange

BEAUTY_SALON_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "A haircut with Ana tomorrow around 11?",
        "[check_availability] Ana is free tomorrow at <free time from the tool>. "
        "Shall I book the haircut with her in your name? [only after a clear "
        "yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is a keratin treatment for long hair?",
        "[get_price: not found] A keratin treatment isn't in our price list, so "
        "I can't give a price. Shall I ask a master to reply?",
    ),
    example(
        Kind.HANDOFF,
        "My nails peeled off after two days, I'm really not happy.",
        "[handoff_to_human: complaint, urgency high] I'm sorry. <what the tool "
        "returned for the customer>",
    ),
]

CLINIC_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "I need an appointment with a dermatologist next week.",
        "[check_availability] <doctor from the facts> is free on <free days and "
        "times from the tool>. Which suits you? I'll repeat the details and book "
        "after your yes. [create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much does an MRI cost?",
        "[get_price: not found] An MRI isn't in our price list, so I can't name "
        "a price. Shall I pass the question to the reception?",
    ),
    example(
        Kind.HANDOFF,
        "I have chest pain and I can't breathe properly.",
        "Please call the emergency number <emergency number> right now. "
        "[handoff_to_human: emergency, urgency critical]",
    ),
]

VETERINARY_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "My cat needs a vaccination, can we come on Wednesday?",
        "[check_availability] A vet is free on Wednesday at <free time from the "
        "tool>. Shall I book the vaccination for your cat? [only after a clear "
        "yes: create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much is dental cleaning for a dog?",
        "[get_price: not found] Dental cleaning isn't in our price list, so I "
        "can't name a price. Shall I ask a vet to reply?",
    ),
    example(
        Kind.HANDOFF,
        "My dog ate chocolate and he is shaking!",
        "Please go to emergency care now: <emergency contact from the facts>. "
        "[handoff_to_human: emergency, urgency critical]",
    ),
]

FITNESS_EXAMPLES: list[NicheExampleExchange] = [
    example(
        Kind.BOOKING_CONFIRMATION,
        "Can I try a yoga class on Thursday evening?",
        "[check_availability] There is a yoga class on Thursday at <time from "
        "the tool>. Shall I sign you up for a trial? [only after a clear yes: "
        "create_booking]",
    ),
    example(
        Kind.PRICE_NOT_FOUND,
        "How much are 10 sessions with a personal trainer?",
        "[get_price: not found] A 10-session package isn't in our price list, "
        "so I can't quote it. Shall I ask a coach to reply?",
    ),
    example(
        Kind.HANDOFF,
        "I want to cancel my membership and get my money back.",
        "[handoff_to_human: non-standard request] <what the tool returned for "
        "the customer>",
    ),
]
