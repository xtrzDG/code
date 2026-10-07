/**
 * The query keys of Settings → Integrations: calendar connections, outbound
 * webhooks and API keys. Spread into `queryKeys`, which documents the key
 * rules.
 */

import type { QueryKey } from "./queryKey";

type Id = string;

export const integrationQueryKeys = {
  integrations: {
    all: (businessId: Id) => ["integrations", businessId] as const,
    /** Settings → Integrations, with each resource's calendars at a glance. */
    list: (businessId: Id) => ["integrations", businessId, "list"] as const,
    /** The connected Google account's calendars to link a resource to. */
    googleCalendars: (businessId: Id) => ["integrations", businessId, "googleCalendars"] as const,
    /** Outbound webhooks with the event catalog. */
    webhooks: (businessId: Id) => ["integrations", businessId, "webhooks"] as const,
    /**
     * One webhook's delivery log, newest first. Not under `webhooks`: a
     * change of the list (`queryCache.update` of its prefix) must not reach
     * a log, whose items are deliveries, not webhooks.
     */
    deliveries: (businessId: Id, webhookId: Id) => ["integrations", businessId, "webhookDeliveries", webhookId] as const,
    /** API keys with the scopes a key may get. */
    apiKeys: (businessId: Id) => ["integrations", businessId, "apiKeys"] as const,
  },
} satisfies Record<string, Record<string, (...args: never[]) => QueryKey>>;
