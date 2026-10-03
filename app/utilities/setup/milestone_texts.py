"""
What staff hear when the business reaches a milestone worth celebrating:
the first real conversation, the first booking made by the assistant, and
the first booking taken while the business was closed. `{name}` is the
business's name.
"""

from app.schemas.constants.setup import ActivationEventKind
from app.schemas.dto.localization import LocalizedText
from app.utilities.knowledge.localized_texts import build_localized_text

# The milestones that get a toast in the cabinet and a push to the team.
CELEBRATED_MILESTONES: frozenset[ActivationEventKind] = frozenset(
    {
        ActivationEventKind.FIRST_CONVERSATION,
        ActivationEventKind.FIRST_BOOKING,
        ActivationEventKind.FIRST_AFTER_HOURS_BOOKING,
    }
)

MILESTONE_TITLES: dict[ActivationEventKind, LocalizedText] = {
    ActivationEventKind.FIRST_CONVERSATION: build_localized_text(
        en="Your assistant answered its first customer",
        ru="Помощник ответил первому клиенту",
        ka="ასისტენტმა პირველ კლიენტს უპასუხა",
    ),
    ActivationEventKind.FIRST_BOOKING: build_localized_text(
        en="The first booking made by your assistant",
        ru="Первая бронь, которую сделал помощник",
        ka="პირველი ჯავშანი, რომელიც ასისტენტმა მიიღო",
    ),
    ActivationEventKind.FIRST_AFTER_HOURS_BOOKING: build_localized_text(
        en="A booking while you were closed",
        ru="Бронь, пока вы были закрыты",
        ka="ჯავშანი, როცა დაკეტილი იყავით",
    ),
}

MILESTONE_DETAILS: dict[ActivationEventKind, LocalizedText] = {
    ActivationEventKind.FIRST_CONVERSATION: build_localized_text(
        en="{name}: a real customer wrote, and the assistant answered.",
        ru="{name}: написал настоящий клиент, и помощник ответил.",
        ka="{name}: ნამდვილმა კლიენტმა მოგწერათ და ასისტენტმა უპასუხა.",
    ),
    ActivationEventKind.FIRST_BOOKING: build_localized_text(
        en="{name}: a customer booked through the assistant.",
        ru="{name}: клиент забронировал через помощника.",
        ka="{name}: კლიენტმა ასისტენტის მეშვეობით დაჯავშნა.",
    ),
    ActivationEventKind.FIRST_AFTER_HOURS_BOOKING: build_localized_text(
        en="{name}: the assistant took a booking outside your opening hours.",
        ru="{name}: помощник принял бронь в нерабочее время.",
        ka="{name}: ასისტენტმა არასამუშაო საათებში მიიღო ჯავშანი.",
    ),
}
