"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconClock } from "@/components/icons";
import { formatLocalDate, formatLocalTime, isLocalDate, isLocalTime } from "@/components/insights/dates";
import type { AvailableSlot } from "@/components/insights/types";
import { Button, ErrorState, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

export interface SlotRequest {
  date: string;
  partySize: number | null;
  resourceId: string | null;
  /** Preferred time: the API returns the free slots nearest to it. */
  time: string | null;
  nights: number | null;
  /** Booked by nights (hotels, rentals): places are offered, not times. */
  isStay: boolean;
}

/**
 * "Show free times": asks GET …/availability for the date (and party,
 * place, preferred time) and offers the free slots as choices.
 */
export function SlotPicker({
  request,
  selected,
  onPick,
}: {
  request: SlotRequest;
  selected: { time: string | null; resourceId: string | null };
  onPick: (slot: AvailableSlot) => void;
}) {
  const { t, tp, locale } = useI18n();
  const { business } = useBusiness();
  const businessId = business.id;
  // The request the shown slots answer; null until the button is pressed.
  const [asked, setAsked] = useState<SlotRequest | null>(null);
  const canAsk = isLocalDate(request.date);
  const isStay = request.isStay;

  const availability = useApiQuery(
    () =>
      api.GET("/v1/businesses/{business_id}/availability", {
        params: {
          path: { business_id: businessId },
          query: {
            date: asked?.date ?? "",
            party_size: asked?.partySize ? String(asked.partySize) : undefined,
            resource_id: asked?.resourceId || undefined,
            time: asked?.time && isLocalTime(asked.time) ? asked.time : undefined,
            nights: asked?.nights ? String(asked.nights) : undefined,
          },
        },
      }),
    [businessId, asked],
    { enabled: asked !== null },
  );

  const isStale =
    asked !== null &&
    (asked.date !== request.date ||
      asked.partySize !== request.partySize ||
      asked.resourceId !== request.resourceId ||
      asked.nights !== request.nights);

  return (
    <div className="space-y-3">
      <Button
        variant="secondary"
        size="sm"
        leadingIcon={<IconClock className="size-4" aria-hidden />}
        disabled={!canAsk}
        onClick={() => (asked && !isStale && asked.time === request.time ? availability.reload() : setAsked(request))}
      >
        {t(isStay ? "bookings.form.findPlaces" : "bookings.form.findSlots")}
      </Button>

      {asked === null ? null : availability.isLoading ? (
        <Spinner size="sm" label={t("common.loading")} className="text-ink-subtle" />
      ) : availability.error ? (
        <ErrorState error={availability.error} onRetry={availability.reload} className="py-4" />
      ) : availability.data ? (
        <div className={cn("space-y-2", isStale && "opacity-50")} aria-live="polite">
          <p className="text-sm font-medium text-ink">
            {t(isStay ? "bookings.form.placesTitle" : "bookings.form.slotsTitle")}
            <span className="font-normal text-ink-muted">
              {" · "}
              {formatLocalDate(asked.date, locale, { weekday: "long", day: "numeric", month: "long" })}
            </span>
          </p>
          {!availability.data.is_open_on_date ? (
            <p className="text-sm text-ink-muted">{t("bookings.form.closedOnDate")}</p>
          ) : (availability.data.slots ?? []).length === 0 ? (
            <p className="text-sm text-ink-muted">{t(isStay ? "bookings.form.noPlaces" : "bookings.form.noSlots")}</p>
          ) : (
            <>
              <ul className="flex flex-wrap gap-2">
                {(availability.data.slots ?? []).map((slot) => {
                  const isSelected = slot.time === selected.time && slot.resource_id === selected.resourceId;
                  return (
                    <li key={`${slot.resource_id}-${slot.time}`}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => onPick(slot)}
                        className={cn(
                          "rounded-lg border px-3 py-1.5 text-sm transition-colors",
                          isSelected
                            ? "border-accent bg-accent-soft text-accent-ink"
                            : "border-line-strong bg-surface text-ink hover:bg-surface-muted",
                        )}
                      >
                        {slot.booking_unit === "night" ? (
                          <>
                            <span dir="auto">{slot.resource_name}</span>
                            <span className="text-ink-muted"> · </span>
                            <span className="font-medium">{tp("bookings.nights", slot.nights ?? 1)}</span>
                          </>
                        ) : (
                          <>
                            <span className="font-medium tabular-nums">{slot.time ? formatLocalTime(slot.time, locale) : ""}</span>
                            <span className="text-ink-muted"> · </span>
                            <span dir="auto">{slot.resource_name}</span>
                          </>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
              <p className="text-xs text-ink-subtle">{t(isStay ? "bookings.form.placesHint" : "bookings.form.slotsHint")}</p>
            </>
          )}
        </div>
      ) : null}
    </div>
  );
}
