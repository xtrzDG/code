from app.contracts.value import NicheValueRegistryContract
from app.registries.niches.niche_value_catalog import NICHE_VALUE_DEFAULTS
from app.schemas.constants.niches import NicheKey
from app.schemas.dto.value.niche_value import NicheValueDefaults


class NicheValueRegistry(NicheValueRegistryContract):
    """
    Read-only catalog of the value estimates of every niche
    (`niche_value_catalog`). Refuses to start without exactly one entry
    per niche, so a new niche cannot ship without its estimates.
    """

    def __init__(
        self,
        defaults: tuple[NicheValueDefaults, ...] = NICHE_VALUE_DEFAULTS,
    ) -> None:
        by_niche: dict[NicheKey, NicheValueDefaults] = {}
        for entry in defaults:
            if entry.niche_key in by_niche:
                raise ValueError(f"Niche {entry.niche_key} has two value entries.")

            by_niche[entry.niche_key] = entry

        missing: list[NicheKey] = [key for key in NicheKey if key not in by_niche]
        if missing:
            raise ValueError(f"Niches without value estimates: {missing}.")

        self._by_niche: dict[NicheKey, NicheValueDefaults] = by_niche

    def get(self, niche_key: NicheKey) -> NicheValueDefaults:
        return self._by_niche[niche_key]
