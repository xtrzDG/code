"use client";

/**
 * How much waits in the inbox (open handoffs, new requests), for the
 * badges on Messages in the sidebar, the tab bar and the Messages tabs, and
 * for the overview. GET …/inbox-counts answers counts only, so it is not an
 * audited view and may be polled: once a minute while the tab is visible,
 * and at once when the person comes back to it. Resolving a handoff or
 * moving a request on invalidates it.
 */

import { createContext, useContext, useMemo, type ReactNode } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useAutoReload } from "@/components/insights/useAutoReload";
import type { InboxCounts } from "@/lib/inboxBadges";

const InboxCountsContext = createContext<InboxCounts | null>(null);

const POLL_MS = 60_000;

function skipReload(): void {}

export function InboxCountsProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const { business } = useBusiness();
  const businessId = business.id;
  const counts = useQuery(
    queryKeys.inbox.counts(businessId),
    () => api.GET("/v1/businesses/{business_id}/inbox-counts", { params: { path: { business_id: businessId } } }),
    { enabled },
  );
  const { reload } = counts;
  useAutoReload(enabled ? reload : skipReload, { intervalMs: enabled ? POLL_MS : null });

  const data = counts.data;
  const value = useMemo<InboxCounts | null>(
    () => (data ? { openHandoffs: data.open_handoff_count, newLeads: data.new_lead_count } : null),
    [data],
  );
  return <InboxCountsContext.Provider value={value}>{children}</InboxCountsContext.Provider>;
}

/** The counts, or null while they load (and before the assistant exists). */
export function useInboxCounts(): InboxCounts | null {
  return useContext(InboxCountsContext);
}
