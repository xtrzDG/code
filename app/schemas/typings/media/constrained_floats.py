"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class Latitude(BaseConstrainedTypedFloat):
    """
    Latitude of a place a customer shared, in degrees north.

    Example:
        latitude = Latitude(41.7151)
    """

    ge = -90.0
    le = 90.0


class Longitude(BaseConstrainedTypedFloat):
    """
    Longitude of a place a customer shared, in degrees east.

    Example:
        longitude = Longitude(44.8271)
    """

    ge = -180.0
    le = 180.0


# Keep abc order for all non example types, if possible.
