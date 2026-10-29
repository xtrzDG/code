/**
 * The query keys of brands (chains of locations), outside any one
 * business. Spread into `queryKeys`, which documents the key rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;

export const brandQueryKeys = {
  brands: {
    /** Every brand-level read: invalidated after any change to a brand. */
    all: () => ["brands"] as const,
    /** The brands the signed-in person belongs to. */
    mine: () => ["brands", "mine"] as const,
    detail: (brandId: Id) => ["brands", brandId, "detail"] as const,
    /** Each reached location's value, sources and waiting work over a period. */
    dashboard: (brandId: Id, period: string) => ["brands", brandId, "dashboard", period] as const,
    /** The facts every location shares, with where they are replaced. */
    knowledge: (brandId: Id) => ["brands", brandId, "knowledge"] as const,
    /** A location's view of its brand's shared answers, with its own replacements. */
    locationShared: (businessId: Id) => ["brands", "location", businessId, "shared"] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
