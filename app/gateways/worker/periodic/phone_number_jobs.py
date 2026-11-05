"""
The periodic jobs of the numbers the platform rents for businesses' phone
lines (1213), on the default lane (the batch worker: they call the carrier
and the voice platform, never in a customer's way):

- `bill_phone_number_rentals` every hour, before the grace job looks for
  unpaid bills: each rental month that began is billed or recorded, and a
  number nobody pays for is given back (`BillPhoneNumberRentalsUseCase`);
- `maintain_phone_numbers` every five minutes: numbers given back are
  returned to the carrier, rented ones kept with the live voice agent,
  fulfilled requests closed (`MaintainPhoneNumbersUseCase`).
"""

from app.contracts.jobs import PeriodicJobOperator
from app.gateways.worker.background_worker import PeriodicJobSpec
from app.schemas.typings.platform.constrained_integers import JobIntervalSeconds
from app.schemas.typings.platform.constrained_strings import JobName

BILL_PHONE_NUMBER_RENTALS_JOB: JobName = JobName("bill_phone_number_rentals")
MAINTAIN_PHONE_NUMBERS_JOB: JobName = JobName("maintain_phone_numbers")
HOURLY: JobIntervalSeconds = JobIntervalSeconds(60 * 60)
EVERY_FIVE_MINUTES: JobIntervalSeconds = JobIntervalSeconds(5 * 60)


def bill_phone_number_rentals_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every hour."""

    return PeriodicJobSpec(
        name=BILL_PHONE_NUMBER_RENTALS_JOB, interval_seconds=HOURLY, operator=operator
    )


def maintain_phone_numbers_job(operator: PeriodicJobOperator) -> PeriodicJobSpec:
    """The periodic job spec that runs `operator` every five minutes."""

    return PeriodicJobSpec(
        name=MAINTAIN_PHONE_NUMBERS_JOB,
        interval_seconds=EVERY_FIVE_MINUTES,
        operator=operator,
    )
