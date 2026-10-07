"""
The sub-processor list (DPA section 8) as data: the single source of the
DPA's table, GET /v1/legal/subprocessors and the change notices to owners.

To add a sub-processor: add its entry (texts in en, ru and ka, the
`app/clients` packages that reach it) with `added_on` at least the notice
period after `addition_announced_on`, the day the change is published.
To remove one: set `removed_on` and `removal_announced_on` the same way.
Then run `uv run python -m scripts.render_subprocessor_table` so the DPA
files show the new table; the owners are told by the
`send_subprocessor_notices` job when the notice period opens.
"""

from app.registries.legal.subprocessor_entries_messaging import (
    MESSAGING_SUBPROCESSORS,
)
from app.registries.legal.subprocessor_entries_models import MODEL_SUBPROCESSORS
from app.registries.legal.subprocessor_entries_platform import (
    PLATFORM_SUBPROCESSORS,
)
from app.schemas.dto.legal import SubprocessorEntry
from app.schemas.typings.legal.constrained_integers import SubprocessorNoticeDays
from app.schemas.typings.legal.constrained_strings import ClientModuleName
from app.schemas.typings.legal.strings import ClientModuleExclusionReason

# DPA section 8.3: owners hear of an addition or a removal this long ahead.
SUBPROCESSOR_NOTICE_DAYS: SubprocessorNoticeDays = SubprocessorNoticeDays(30)

# The order of the DPA's table.
TABLE_ORDER: tuple[str, ...] = (
    "openai",
    "elevenlabs",
    "zadarma",
    "meta",
    "telegram",
    "flitt",
    "langfuse",
    "sentry",
    "render",
    "google_calendar",
    "anthropic",
    "anthropic_quality_review",
    "cloudflare_turnstile",
    "object_storage",
    "email",
    "twilio",
    "web_push",
)

_ENTRIES_BY_KEY: dict[str, SubprocessorEntry] = {
    str(entry.key): entry
    for entry in (
        *MODEL_SUBPROCESSORS,
        *MESSAGING_SUBPROCESSORS,
        *PLATFORM_SUBPROCESSORS,
    )
}

SUBPROCESSORS: tuple[SubprocessorEntry, ...] = tuple(
    _ENTRIES_BY_KEY[entry_key] for entry_key in TABLE_ORDER
) + tuple(
    entry
    for entry_key, entry in _ENTRIES_BY_KEY.items()
    if entry_key not in TABLE_ORDER
)

# The `app/clients` packages that reach no sub-processor, and why. Every
# other package must be named by an entry (tests/legal).
CLIENT_MODULES_WITHOUT_SUBPROCESSOR: dict[
    ClientModuleName, ClientModuleExclusionReason
] = {
    ClientModuleName("ecb"): ClientModuleExclusionReason(
        "Reads the European Central Bank's public exchange rates; sends no "
        "personal data."
    ),
    ClientModuleName("nbg"): ClientModuleExclusionReason(
        "Reads the National Bank of Georgia's public exchange rates; sends no "
        "personal data."
    ),
    ClientModuleName("http"): ClientModuleExclusionReason(
        "Fetches the public web pages an owner names for the website import "
        "and the files customers send through the messaging platforms listed "
        "(Meta, Telegram); sends no personal data of its own."
    ),
    ClientModuleName("cal_com"): ClientModuleExclusionReason(
        "Reads busy times from, and writes the bookings of a resource to, the "
        "Cal.com account an owner connects with the owner's own API key: the "
        "Client's own processor, reached on the Client's instruction. A "
        "written booking carries its time, the guest's name, the business's "
        "time zone and the guest's language."
    ),
}
