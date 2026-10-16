"""Keep abc order."""

from base_typed_string import BaseTypedString


class AlertDetailText(BaseTypedString):
    """
    What a platform alert found, in one English line for the team (the
    figure, its threshold and where it shows): never personal data.
    """


class AlertRuleSummary(BaseTypedString):
    """What a platform alert rule watches, in one English sentence."""


class MaintenanceErrorText(BaseTypedString):
    """Why a backup or a restore drill failed, in one line from the tool."""


class PlatformAlertMessage(BaseTypedString):
    """The text of one platform alert as the platform bot or e-mail sends it."""


# Keep abc order for all non example types, if possible.
