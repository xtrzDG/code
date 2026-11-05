from enum import StrEnum


class SecurityNudgeReason(StrEnum):
    """
    Why an owner of a live business without a second factor is reminded to
    turn one on: their customers' data is in the cabinet
    (PROTECT_CUSTOMERS), or they put the reminder away while working alone
    and the team has grown since (TEAM_GREW): every new person is another
    way in.
    """

    PROTECT_CUSTOMERS = "protect_customers"
    TEAM_GREW = "team_grew"
