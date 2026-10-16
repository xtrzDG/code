"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { CALENDAR_REFUSAL_MESSAGES, type BookingSystemLinkBody } from "@/lib/resourceCalendar";

/**
 * One resource's calendars and every change to them. A change answers with
 * the resource's calendars as they are now (read again at once), which
 * replace the cached ones; a removal (204) loads them again. Settings →
 * Integrations and the resources list (their summaries) reload too.
 */
export function useResourceCalendar(resourceId: string) {
  const { business } = useBusiness();
  const key = queryKeys.resources.calendar(business.id, resourceId);
  const path = { business_id: business.id, resource_id: resourceId };
  const view = useQuery(key, () => api.GET("/v1/businesses/{business_id}/resources/{resource_id}/calendar", { params: { path } }));
  const changed = { invalidate: [queryKeys.integrations.all(business.id)], reasonMessages: CALENDAR_REFUSAL_MESSAGES };
  const removed = { ...changed, invalidate: [key, queryKeys.integrations.all(business.id)] };

  const sync = useMutation(() => api.POST("/v1/businesses/{business_id}/resources/{resource_id}/calendar/sync", { params: { path } }), changed);
  const linkGoogle = useMutation(
    (calendarId: string) => api.PUT("/v1/businesses/{business_id}/resources/{resource_id}/calendar/google", { params: { path }, body: { calendar_id: calendarId } }),
    changed,
  );
  const unlinkGoogle = useMutation(() => api.DELETE("/v1/businesses/{business_id}/resources/{resource_id}/calendar/google", { params: { path } }), removed);
  const importFeed = useMutation(
    (url: string) => api.POST("/v1/businesses/{business_id}/resources/{resource_id}/calendar/ical-imports", { params: { path }, body: { url } }),
    changed,
  );
  const removeFeed = useMutation(
    (feedId: string) =>
      api.DELETE("/v1/businesses/{business_id}/resources/{resource_id}/calendar/ical-imports/{feed_id}", { params: { path: { ...path, feed_id: feedId } } }),
    removed,
  );
  const linkBookingSystem = useMutation(
    (body: BookingSystemLinkBody) => api.PUT("/v1/businesses/{business_id}/resources/{resource_id}/calendar/booking-system", { params: { path }, body }),
    changed,
  );
  const unlinkBookingSystem = useMutation(
    () => api.DELETE("/v1/businesses/{business_id}/resources/{resource_id}/calendar/booking-system", { params: { path } }),
    removed,
  );
  const createExport = useMutation(() => api.POST("/v1/businesses/{business_id}/resources/{resource_id}/calendar/ical-export", { params: { path } }), changed);
  const removeExport = useMutation(() => api.DELETE("/v1/businesses/{business_id}/resources/{resource_id}/calendar/ical-export", { params: { path } }), removed);

  return {
    view,
    sync,
    linkGoogle,
    unlinkGoogle,
    importFeed,
    removeFeed,
    linkBookingSystem,
    unlinkBookingSystem,
    createExport,
    removeExport,
  };
}

export type ResourceCalendarState = ReturnType<typeof useResourceCalendar>;

/** The connected Google account's calendars, loaded only when asked for. */
export function useGoogleCalendars(enabled: boolean) {
  const { business } = useBusiness();
  return useQuery(
    queryKeys.integrations.googleCalendars(business.id),
    () =>
      api.GET("/v1/businesses/{business_id}/integrations/google-calendar/calendars", {
        params: { path: { business_id: business.id } },
      }),
    { enabled },
  );
}
