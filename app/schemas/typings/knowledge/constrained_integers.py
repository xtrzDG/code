"""Keep abc order."""

from base_typed_int import BaseConstrainedTypedInt


class KnowledgeSearchLimit(BaseConstrainedTypedInt):
    """How many knowledge items a search returns (concept: up to 5)."""

    ge = 1
    le = 20


class ServiceDurationMinutes(BaseConstrainedTypedInt):
    """Duration of a service from the price list, in minutes."""

    ge = 1
    le = 43200


# Keep abc order for all non example types, if possible.
