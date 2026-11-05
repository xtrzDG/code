"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class ExtractionConfidence(BaseConstrainedTypedFloat):
    """Model's confidence in one line read from a menu or price list, 0.0 to 1.0."""

    ge = 0.0
    le = 1.0


# Keep abc order for all non example types, if possible.
