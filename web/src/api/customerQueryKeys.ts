/**
 * The query keys of the customers section: the list and its filters, one
 * customer, the standing shown over a conversation, the settings and tags,
 * saved segments and the command palette's search. Spread into `queryKeys`,
 * which documents the key rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;

export const customerQueryKeys = {
  customers: {
    all: (businessId: Id) => ["customers", businessId] as const,
    /** The list with its search, tag and VIP/blocked filter (serialized). */
    list: (businessId: Id, filters: string) => ["customers", businessId, "list", filters] as const,
    /** One customer's page (audited as a view by the API). */
    detail: (businessId: Id, contactId: Id) => ["customers", businessId, "detail", contactId] as const,
    /** "Regular customer · 4 visits" over a conversation. */
    standing: (businessId: Id, contactId: Id) => ["customers", businessId, "standing", contactId] as const,
    /** Whether staff see phones; the business's tags. */
    settings: (businessId: Id) => ["customers", businessId, "settings"] as const,
    segments: (businessId: Id) => ["customers", businessId, "segments"] as const,
    members: (businessId: Id, segmentId: Id) => ["customers", businessId, "members", segmentId] as const,
    /** How many customers rules hold (serialized rules). */
    preview: (businessId: Id, rules: string) => ["customers", businessId, "preview", rules] as const,
    /** The command palette's search. */
    search: (businessId: Id, text: string) => ["customers", businessId, "search", text] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
