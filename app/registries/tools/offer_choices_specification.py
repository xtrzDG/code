"""The offer_choices model tool: options the customer taps instead of typing."""

from app.registries.tools.tool_schema_parts import (
    JsonSchema,
    object_schema,
    string_list_property,
    string_property,
)

OFFER_CHOICES_SPECIFICATION: tuple[str, JsonSchema] = (
    "Show the customer 2 to 10 short options to tap instead of typing: the "
    "free times check_availability returned, or a confirmation such as 'Yes, "
    "book it' and 'Another time' before create_booking. The options appear "
    "as buttons under your reply, after prompt_text: write the reply as "
    "usual, without listing the options or repeating the question. Offer "
    "only times, prices, names and services from the facts or tool results. "
    "A tap comes back as the option's text (or, on a channel without "
    "buttons, its number).",
    object_schema(
        {
            "prompt_text": string_property(
                "The question shown with the options, in the customer's "
                "language, one line of at most 200 characters, e.g. 'Which "
                "time suits you?'."
            ),
            "options": string_list_property(
                "2 to 10 different options in the customer's language, each "
                "at most 20 characters without line breaks, e.g. ['18:00', "
                "'19:30', '21:00'] or ['Yes, book it', 'Another time']."
            ),
        }
    ),
)
