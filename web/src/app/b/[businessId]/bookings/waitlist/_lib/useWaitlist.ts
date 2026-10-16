"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useCursorPage } from "@/api/useCursorPage";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import type { WaitlistEntry, WaitlistFilter, WaitlistPage } from "./waitlistModel";

const PAGE_SIZE = 30;

/**
 * Bookings → Waitlist of the current business: one list's entries (a view
 * the API audits), the settings with the counts by status, taking an entry
 * off the list, and (owners) saving the settings. A change anywhere (a
 * customer joins, a place is held or taken) reaches the page as the live
 * event `waitlist.changed`.
 */
export function useWaitlist(filter: WaitlistFilter) {
  const { business } = useBusiness();
  const path = { business_id: business.id };
  const entries = useCursorPage<WaitlistEntry, WaitlistPage>(
    queryKeys.bookings.waitlist(business.id, filter),
    ({ cursor, limit }) =>
      api.GET("/v1/businesses/{business_id}/waitlist", {
        params: { path, query: { filter, limit: String(limit), cursor: cursor ?? undefined } },
      }),
    { pageSize: PAGE_SIZE },
  );
  const settings = useQuery(queryKeys.bookings.waitlistSettings(business.id), () =>
    api.GET("/v1/businesses/{business_id}/waitlist-settings", { params: { path } }),
  );
  const remove = useMutation(
    (entry: WaitlistEntry) =>
      api.DELETE("/v1/businesses/{business_id}/waitlist/{entry_id}", {
        params: { path: { ...path, entry_id: entry.id } },
      }),
    {
      errorToast: false,
      optimistic: (entry) => {
        const before = entries.items ?? [];
        entries.updateItems((items) => items.filter((item) => item.id !== entry.id));
        return () => entries.updateItems(() => before);
      },
      // The counts reload; the lists (audited views) only when next shown: the row is gone already.
      invalidate: [queryKeys.bookings.waitlistSettings(business.id)],
      stale: [queryKeys.bookings.waitlistAll(business.id)],
    },
  );
  const save = useMutation(
    (body: { is_enabled: boolean; hold_minutes: number }) =>
      api.PUT("/v1/businesses/{business_id}/waitlist-settings", { params: { path }, body }),
    { errorToast: false },
  );
  return { entries, settings, remove, save };
}

export type WaitlistState = ReturnType<typeof useWaitlist>;
