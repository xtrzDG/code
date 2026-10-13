/**
 * The query keys of deposits: a business's deposit settings (payment pages
 * and policies), one deposit asked, and the Reports card. Spread into
 * `queryKeys`, which documents the key rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;

export const depositQueryKeys = {
  deposits: {
    all: (businessId: Id) => ["deposits", businessId] as const,
    /** Settings → Deposits, and the policies the resource and service editors show. */
    settings: (businessId: Id) => ["deposits", businessId, "settings"] as const,
    /** One deposit asked: its reference and payment page (a booking's details). */
    request: (businessId: Id, requestId: Id) => ["deposits", businessId, "request", requestId] as const,
    /** Reports → Deposits for the last `days`. */
    report: (businessId: Id, days: number) => ["deposits", businessId, "report", days] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
