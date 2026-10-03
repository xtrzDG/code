"use client";

/**
 * The live cabinet of a business: one event stream per tab keeps every
 * shown list fresh (src/api/events.ts), the attention counts behind the
 * navigation badges and the tab title reload with each change, and a
 * customer who needs a person brings a toast (and, if the person turned it
 * on, a chime). The counts are counts only (no audit entry); without a
 * live stream they are polled once a minute instead.
 */

import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useMemo, type ReactNode } from "react";

import { api } from "@/api/client";
import type { LiveStreamStatus } from "@/api/events";
import type { LiveEvent } from "@/api/liveEvents";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { useAutoReload } from "@/components/insights/useAutoReload";
import { useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import type { AttentionCounts } from "@/lib/inboxBadges";
import { businessLocation, businessPath } from "@/lib/navigation";
import { canOpenPage } from "@/lib/sections";

import { playChime, useChimePreference, useChimeUnlock } from "./chime";
import { useDocumentTitleCount } from "./useDocumentTitleCount";
import { useLiveStream } from "./useLiveStream";
import { useMemberRole } from "./useMemberRole";

export interface LiveCabinet {
  counts: AttentionCounts | null;
  status: LiveStreamStatus;
  reconnect: () => void;
}

const LiveContext = createContext<LiveCabinet | null>(null);

const FALLBACK_POLL_MS = 60_000;

function skipReload(): void {}

function useLoadedAttentionCounts(businessId: string, enabled: boolean, isLive: boolean): AttentionCounts | null {
  const counts = useQuery(
    queryKeys.inbox.counts(businessId),
    () => api.GET("/v1/businesses/{business_id}/attention-counts", { params: { path: { business_id: businessId } } }),
    { enabled },
  );
  const poll = enabled && !isLive;
  useAutoReload(poll ? counts.reload : skipReload, { intervalMs: poll ? FALLBACK_POLL_MS : null });
  const data = counts.data;
  return useMemo<AttentionCounts | null>(
    () =>
      data
        ? {
            openHandoffs: data.open_handoff_count,
            newLeads: data.new_lead_count,
            unconfirmedBookings: data.unconfirmed_booking_count,
            channelErrors: data.channel_error_count,
          }
        : null,
    [data],
  );
}

export function LiveEventsProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const { t } = useI18n();
  const toast = useToast();
  const router = useRouter();
  const { business } = useBusiness();
  const [isChimeOn] = useChimePreference();
  useChimeUnlock(isChimeOn);

  const pathname = usePathname();
  const onEvent = (event: LiveEvent) => {
    if (event.event !== "handoff.created") {
      return;
    }
    if (isChimeOn) {
      playChime();
    }
    if (businessLocation(pathname)?.page === "messages/handoffs") {
      // The list in front of the person shows it already.
      return;
    }
    toast.show({
      tone: "info",
      title: t("live.needsPersonTitle"),
      durationMs: 10_000,
      action: {
        label: t("live.needsPersonOpen"),
        onAction: () => router.push(businessPath(business.id, "messages/handoffs")),
      },
    });
  };
  const { status, reconnect } = useLiveStream(business.id, enabled, onEvent);
  const counts = useLoadedAttentionCounts(business.id, enabled, status === "live");
  const role = useMemberRole();
  const waiting = counts
    ? counts.openHandoffs +
      counts.newLeads +
      counts.unconfirmedBookings +
      (canOpenPage("assistant/channels", role) ? counts.channelErrors : 0)
    : 0;
  useDocumentTitleCount(enabled ? waiting : 0);
  const value = useMemo<LiveCabinet>(() => ({ counts, status, reconnect }), [counts, status, reconnect]);
  return <LiveContext.Provider value={value}>{children}</LiveContext.Provider>;
}

/** The attention counts, or null while they load (and before the assistant exists). */
export function useAttentionCounts(): AttentionCounts | null {
  return useContext(LiveContext)?.counts ?? null;
}

/** The live stream's state; null outside a business (the admin pages). */
export function useLiveCabinet(): LiveCabinet | null {
  return useContext(LiveContext);
}
