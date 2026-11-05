from enum import StrEnum


class BrandMemberRole(StrEnum):
    """
    Role of a person in a brand's team (a chain of locations).

    BRAND_OWNER runs every location of the brand as its owner (billing,
    settings, the team, the shared knowledge). REGIONAL_MANAGER runs only
    the locations assigned to them, with a staff member's rights there;
    the brand's other locations stay closed to them.
    """

    BRAND_OWNER = "brand_owner"
    REGIONAL_MANAGER = "regional_manager"
