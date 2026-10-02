"""Keep abc order."""

from base_typed_string import BaseTypedString


class StaffAlertDetail(BaseTypedString):
    """
    The short second line of a staff alert on a lock screen, by SMS or in an
    e-mail: what happened, without the customer's details (no transcript,
    no phone number).
    """


class StaffAlertTitle(BaseTypedString):
    """
    The first line of a staff alert: the notification title on a device,
    the e-mail subject.
    """


# Keep abc order for all non example types, if possible.
