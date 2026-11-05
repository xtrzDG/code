from app.contracts.growth import RebookingRuleRegistryContract
from app.registries.niches.rebooking_rule_catalog import NICHE_REBOOKING_RULES
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.growth.rebooking_rules import RebookingRule


class RebookingRuleRegistry(RebookingRuleRegistryContract):
    """
    Read-only catalog of each niche's default rebooking rule
    (`rebooking_rule_catalog`). Refuses to start without exactly one rule
    per niche, so a new niche cannot ship without one.
    """

    def __init__(
        self, rules: tuple[RebookingRule, ...] = NICHE_REBOOKING_RULES
    ) -> None:
        by_niche: dict[NicheKey, RebookingRule] = {}
        for rule in rules:
            if rule.niche_key in by_niche:
                raise ValueError(f"Niche {rule.niche_key} has two rebooking rules.")

            by_niche[rule.niche_key] = rule

        missing: list[NicheKey] = [key for key in NicheKey if key not in by_niche]
        if missing:
            raise ValueError(f"Niches without a rebooking rule: {missing}.")

        self._by_niche: dict[NicheKey, RebookingRule] = by_niche

    def get(self, niche_key: NicheKey) -> RebookingRule:
        return self._by_niche[niche_key]
