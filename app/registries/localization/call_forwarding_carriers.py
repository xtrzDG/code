"""
The mobile carriers of the first markets and what their owners need to
know about forwarding (texts: `forwarding.carriers.<country>.<carrier>.note`
in the owner text catalog).

Georgia: Magti publishes the GSM codes (*61, *67, *62, concept "Стек");
Silknet and Cellfie are not confirmed yet. The next markets (Armenia,
Azerbaijan, Ukraine, Turkey, Germany, Israel) are drafts (NEEDS_REVIEW):
their carriers run GSM networks that take the same codes, but nobody has
checked the codes against each carrier's own documentation yet, so the
cabinet says so next to each carrier. What is known of a carrier comes from
public sources and wants the same check before it is marked REVIEWED:

- Team Telecom Armenia: forwarding is free, forwarded calls are billed as
  outgoing ones, an unanswered call is forwarded after 30 seconds by
  default (telecomarmenia.am, "Call Forwarding").
- Turkcell lists **61*, **67* and **62* on its support pages
  (turkcell.com.tr, "Telefona cevap verilmediğinde...").
- Germany: unanswered calls go to the carrier's mailbox by default
  (Telekom 3311, Vodafone 5500, O2 333; giga.de); a no-answer code of
  one's own replaces that forwarding.
- Ukraine: Vodafone also cancels each condition alone (##61#, ##67#,
  ##62#); Kyivstar's ##002# cancels all; forwarded calls are billed as
  outgoing calls under the tariff.
"""

from app.registries.localization.call_forwarding_texts import GSM_CODE_TEMPLATES
from app.schemas.constants.localization import TextReviewStatus
from app.schemas.dto.catalog.call_forwarding import CarrierForwardingGuide
from app.schemas.typings.localization.constrained_strings import CountryCode
from app.schemas.typings.localization.strings import CarrierName
from app.utilities.localization.owner_texts import has_owner_text, owner_text


def carrier(
    country: str,
    slug: str,
    name: str,
    review_status: TextReviewStatus = TextReviewStatus.NEEDS_REVIEW,
) -> CarrierForwardingGuide:
    """A carrier with the GSM codes and its catalog note, when it has one."""

    note_key: str = f"forwarding.carriers.{country}.{slug}.note"
    return CarrierForwardingGuide(
        carrier_name=CarrierName(name),
        code_templates=list(GSM_CODE_TEMPLATES),
        notes=owner_text(note_key) if has_owner_text(note_key) else None,
        review_status=review_status,
    )


CARRIER_GUIDES_BY_COUNTRY: dict[CountryCode, tuple[CarrierForwardingGuide, ...]] = {
    CountryCode("GE"): (
        carrier("ge", "magti", "Magti", TextReviewStatus.REVIEWED),
        carrier("ge", "silknet", "Silknet"),
        carrier("ge", "cellfie", "Cellfie"),
    ),
    CountryCode("AM"): (
        carrier("am", "team_telecom", "Team Telecom Armenia"),
        carrier("am", "viva", "Viva"),
        carrier("am", "ucom", "Ucom"),
    ),
    CountryCode("AZ"): (
        carrier("az", "azercell", "Azercell"),
        carrier("az", "bakcell", "Bakcell"),
        carrier("az", "nar", "Nar"),
    ),
    CountryCode("UA"): (
        carrier("ua", "kyivstar", "Kyivstar"),
        carrier("ua", "vodafone", "Vodafone Ukraine"),
        carrier("ua", "lifecell", "lifecell"),
    ),
    CountryCode("TR"): (
        carrier("tr", "turkcell", "Turkcell"),
        carrier("tr", "vodafone", "Vodafone"),
        carrier("tr", "turk_telekom", "Türk Telekom"),
    ),
    CountryCode("DE"): (
        carrier("de", "telekom", "Telekom"),
        carrier("de", "vodafone", "Vodafone"),
        carrier("de", "o2", "O2"),
    ),
    CountryCode("IL"): (
        carrier("il", "partner", "Partner"),
        carrier("il", "cellcom", "Cellcom"),
        carrier("il", "pelephone", "Pelephone"),
        carrier("il", "hot_mobile", "HOT Mobile"),
    ),
}
