"""One number found in a text, with every reading it may have."""

from dataclasses import dataclass, field
from decimal import Decimal

type LocalTime = tuple[int, int]
type PartialDate = tuple[int | None, int, int]


@dataclass(frozen=True)
class NumberMention:
    """
    One number in a text with every reading it may have (technical record).

    `text` is the mention as written, with its currency, month or meridiem.
    """

    text: str
    start: int
    end: int
    is_money: bool = False
    is_percent: bool = False
    amounts: frozenset[Decimal] = field(default_factory=frozenset[Decimal])
    times: frozenset[LocalTime] = field(default_factory=frozenset[LocalTime])
    dates: frozenset[PartialDate] = field(default_factory=frozenset[PartialDate])
    phone_digits: str | None = None

    @property
    def is_plain_number(self) -> bool:
        """Only a numeric reading: not money, a percentage, time, date or phone."""

        return (
            not self.is_money
            and not self.is_percent
            and not self.times
            and not self.dates
            and self.phone_digits is None
        )
