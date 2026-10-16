"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class ExchangeRate(BaseConstrainedTypedFloat):
    """
    Units of the quote currency for one unit of the base currency (> 0).

    Example:
        eur_to_gel = ExchangeRate(2.9552)
    """

    gt = 0.0


class GrossMarginPercent(BaseConstrainedTypedFloat):
    """
    Revenue minus provider cost as a percent of revenue (negative for a loss).

    Example:
        voice_plan_margin = GrossMarginPercent(68.6)
    """

    le = 100.0


# Keep abc order for all non example types, if possible.
