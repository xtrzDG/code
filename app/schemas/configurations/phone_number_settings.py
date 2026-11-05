from base_pydantic_schemas import ImmutableDTO

from app.schemas.constants.phone_numbers import PhoneNumberProvider
from app.schemas.typings.telephony.constrained_integers import (
    PhoneNumberPriceMarkupPercent,
)


class PhoneNumberSettings(ImmutableDTO):
    """
    Numbers the platform rents for businesses from the cabinet (W21):

    - `provider` (PHONE_NUMBER_PROVIDER: `twilio`, empty by default): the
      carrier that sells the numbers. Twilio uses TWILIO_ACCOUNT_SID and
      TWILIO_AUTH_TOKEN, and the voice platform imports its numbers with
      ELEVENLABS_API_KEY. Without a provider (or a key it needs) owners
      ask the platform team for a number instead;
    - `price_markup_percent` (PHONE_NUMBER_PRICE_MARKUP_PERCENT, 30): what
      the platform adds to the carrier's monthly price before it becomes
      the owner's price, converted to the business's currency at the
      official rate and rounded up to a whole unit.
    """

    provider: PhoneNumberProvider | None = None
    price_markup_percent: PhoneNumberPriceMarkupPercent = PhoneNumberPriceMarkupPercent(
        30
    )
