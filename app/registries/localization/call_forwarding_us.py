"""
United States: forwarding by carrier (texts: `forwarding.us.*`,
`forwarding.star_codes.*` and `forwarding.carriers.us.<carrier>.note` in
the owner text catalog).

US carriers take different codes and number formats, so the owner opens
their carrier first; every other carrier gets the standard GSM codes with
the number as 1 and 10 digits. A code that forwards every call (Verizon's
*72, the *21* codes) is never listed: staff answer first.

What is known comes from search summaries of the carriers' pages, which
could not be opened where this was written, so every carrier is a draft
(NEEDS_REVIEW) until a person checks the pages:

- Verizon: *71 and the 10 digits forwards busy and unanswered calls after
  3 to 6 rings, *73 switches forwarding off; no code for a phone that is
  off or out of coverage (verizon.com/support/call-forwarding-faqs,
  verizon.com/support/knowledge-base-181139).
- T-Mobile: **61*, **67* and **62* with 1 and the 10 digits, an optional
  **NN delay before the last # of the no-answer code; ##004# brings the
  voicemail forwarding back; never an international target
  (t-mobile.com/support/plans-features/self-service-short-codes and
  /calling-services).
- AT&T documents only *21* and #21# (every call) and the phone's call
  forwarding settings (att.com/device-support/article/140337): the
  standard codes, with the 10 digits of AT&T's own *21* example
  (att.com/support/article/wireless/KM1062174).
- Google Fi forwards only every call and US Cellular (now T-Mobile) has no
  verified codes: their owners use the standard codes of other carriers.
"""

from app.registries.localization.call_forwarding_texts import (
    carrier,
    gsm_code_templates,
)
from app.schemas.constants.localization import (
    ForwardingNumberFormat,
    StarCodeCondition,
)
from app.schemas.dto.catalog.call_forwarding import (
    CarrierForwardingGuide,
    CountryForwardingTexts,
    StarCodeTemplate,
)
from app.schemas.typings.localization.constrained_strings import (
    CallForwardingDialCodeTemplate,
    VerticalServiceDialCodeTemplate,
)
from app.utilities.localization.owner_texts import owner_text, owner_text_list

VERIZON_STAR_CODE_TEMPLATES: tuple[StarCodeTemplate, ...] = (
    StarCodeTemplate(
        condition=StarCodeCondition.NO_ANSWER_OR_BUSY,
        dial_code_template=VerticalServiceDialCodeTemplate("*71{number}"),
        descriptions=owner_text("forwarding.star_codes.no_answer_or_busy"),
    ),
    StarCodeTemplate(
        condition=StarCodeCondition.CANCEL_ALL,
        dial_code_template=VerticalServiceDialCodeTemplate("*73"),
        descriptions=owner_text("forwarding.star_codes.cancel_all"),
    ),
)
US_CARRIERS: tuple[CarrierForwardingGuide, ...] = (
    carrier(
        "us",
        "verizon",
        "Verizon",
        code_templates=(),
        star_code_templates=VERIZON_STAR_CODE_TEMPLATES,
    ),
    carrier(
        "us",
        "t_mobile",
        "T-Mobile",
        code_templates=gsm_code_templates(
            ForwardingNumberFormat.DIGITS_WITH_COUNTRY_CODE,
            CallForwardingDialCodeTemplate("##004#"),
        ),
    ),
    carrier(
        "us",
        "att",
        "AT&T",
        code_templates=gsm_code_templates(ForwardingNumberFormat.NATIONAL_DIGITS),
    ),
)
US_FORWARDING_TEXTS: CountryForwardingTexts = CountryForwardingTexts(
    code_templates=list(
        gsm_code_templates(ForwardingNumberFormat.DIGITS_WITH_COUNTRY_CODE)
    ),
    steps=list(owner_text_list("forwarding.us.steps")),
    notes=list(owner_text_list("forwarding.us.notes")),
    is_carrier_choice_needed=True,
)
