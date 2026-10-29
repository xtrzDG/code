/**
 * The query keys of closing a business and deleting accounts: where a
 * business stands on its way out (the banner and Settings → Business), and
 * the signed-in person's deleted businesses (Account → Security). Spread
 * into `queryKeys`, which documents the key rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;

export const closureQueryKeys = {
  closure: {
    /** `GET /v1/businesses/{id}/closure`: active, closing (with its countdown) or being deleted. */
    detail: (businessId: Id) => ["closure", businessId] as const,
  },

  businessDeletions: {
    /** `GET /v1/me/business-deletions`: the businesses this person owned that are deleted. */
    list: () => ["businessDeletions"] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
