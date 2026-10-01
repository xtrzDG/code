"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class ExchangeRate(BaseConstrainedTypedFloat):
    """
    Units of the quote currency for one unit of the base currency (> 0).

    Example:
        eur_to_gel = ExchangeRate(2.9552)
    """

    gt = 0.0


# Keep abc order for all non example types, if possible.
