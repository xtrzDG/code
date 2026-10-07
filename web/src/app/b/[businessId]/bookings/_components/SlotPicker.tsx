"use client";

import { useState } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconClock } from "@/components/icons";
import { formatLocalDate, formatLocalTime, isLocalDate, isLocalTime } from "@/components/insights/dates";
import type { AvailableSlot } from "@/components/insights/types";
import { Button, ErrorState, Spinner } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { groupSlotsByResource } from "../_lib/manualBooking";

export interface SlotRequest {
  date: string;
  partySize: number | null;
  resourceId: string | null;
  /** Preferred time: the API returns the free slots nearest to it. */
  time: string | null;
  nights: number | null;
  /** Booked by nights (hotels, rentals): places are offered, not times. */
  isStay: boolean;
  /** The service, package or room type: only its performers, for its length. */
  serviceId: string | null;
  /** A length other than the service's usual one. */
  durationMinutes: number | null;
}

type SlotMode = "nearest" | "day";

interface AskedSlots extends SlotRequest {
  mode: SlotMode;
}

/**
 * "Show free times": asks GET …/availability for the date (and party,
 * place, preferred time) and offers the free slots as choices. "Whole day"
 * lists every free slot of the date for every place (the staff view: no
 * advance notice, no online party limit).
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
  // The request the shown slots answer; null until a button is pressed.
  const [asked, setAsked] = useState<AskedSlots | null>(null);
  const canAsk = isLocalDate(request.date);
  const isStay = request.isStay;

  const availability = useQuery(
    queryKeys.bookings.availability(businessId, JSON.stringify(asked)),
    () =>
      api.GET("/v1/businesses/{business_id}/availability", {
        params: {
          path: { business_id: businessId },
          query: {
            date: asked?.date ?? "",
            party_size: asked?.partySize ? String(asked.partySize) : undefined,
            resource_id: asked?.resourceId || undefined,
            time: asked?.mode === "nearest" && asked.time && isLocalTime(asked.time) ? asked.time : undefined,
            nights: asked?.nights ? String(asked.nights) : undefined,
            service_item_id: asked?.serviceId ?? undefined,
            duration_minutes: asked?.durationMinutes ? String(asked.durationMinutes) : undefined,
            full_day: asked?.mode === "day" ? "true" : undefined,
          },
        },
      }),
    // Free slots change with every booking: always ask again.
    { enabled: asked !== null, staleMs: 0 },
  );

  const isStale =
    asked !== null &&
    (asked.date !== request.date ||
      asked.partySize !== request.partySize ||
      (asked.resourceId !== null && asked.resourceId !== request.resourceId) ||
      asked.nights !== request.nights ||
      asked.serviceId !== request.serviceId ||
      asked.durationMinutes !== request.durationMinutes);

  const ask = (mode: SlotMode) =>
    asked && !isStale && asked.mode === mode && (mode === "day" || asked.time === request.time)
      ? availability.reload()
      : setAsked({ ...request, mode });
  const slots = availability.data?.slots ?? [];
  const isDay = asked?.mode === "day";

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="secondary"
          size="sm"
          leadingIcon={<IconClock className="size-4" aria-hidden />}
          disabled={!canAsk}
          aria-pressed={asked !== null ? asked.mode === "nearest" : undefined}
          onClick={() => ask("nearest")}
        >
          {t(isStay ? "bookings.form.findPlaces" : "bookings.form.findSlots")}
        </Button>
        {isStay ? null : (
          <Button
            variant="ghost"
            size="sm"
            disabled={!canAsk}
            aria-pressed={asked !== null ? asked.mode === "day" : undefined}
            onClick={() => ask("day")}
          >
            {t("bookings.form.wholeDay")}
          </Button>
        )}
      </div>

      {asked === null ? null : availability.isLoading || availability.isFetching ? (
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
          ) : slots.length === 0 ? (
            <p className="text-sm text-ink-muted">
              {t(isStay ? "bookings.form.noPlaces" : isDay ? "bookings.form.noSlotsDay" : "bookings.form.noSlots")}
            </p>
          ) : isDay ? (
            <DaySlots slots={slots} selected={selected} onPick={onPick} />
          ) : (
            <>
              <ul className="flex flex-wrap gap-2">
                {slots.map((slot) => {
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
                            <span dir="auto" data-user-content>{slot.resource_name}</span>
                            <span className="text-ink-muted"> · </span>
                            <span className="font-medium">{tp("bookings.nights", slot.nights ?? 1)}</span>
                          </>
                        ) : (
                          <>
                            <span className="font-medium tabular-nums">{slot.time ? formatLocalTime(slot.time, locale) : ""}</span>
                            <span className="text-ink-muted"> · </span>
                            <span dir="auto" data-user-content>{slot.resource_name}</span>
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

/** Every free slot of the day, one row of times per place. */
function DaySlots({
  slots,
  selected,
  onPick,
}: {
  slots: readonly AvailableSlot[];
  selected: { time: string | null; resourceId: string | null };
  onPick: (slot: AvailableSlot) => void;
}) {
  const { t, tp, locale } = useI18n();
  const byResource = groupSlotsByResource(slots);
  return (
    <div className="space-y-3">
      {byResource.map((group) => (
        <section key={group.resourceId} aria-label={group.resourceName}>
          <h4 className="mb-1.5 flex items-baseline gap-2 text-sm">
            <span dir="auto" data-user-content className="font-medium text-ink">
              {group.resourceName}
            </span>
            <span className="text-xs text-ink-subtle">{tp("bookings.form.freeTimes", group.slots.length)}</span>
          </h4>
          <ul className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto">
            {group.slots.map((slot) => {
              const isSelected = slot.time === selected.time && slot.resource_id === selected.resourceId;
              return (
                <li key={slot.time}>
                  <button
                    type="button"
                    aria-pressed={isSelected}
                    aria-label={t("bookings.form.pickSlot", {
                      time: slot.time ? formatLocalTime(slot.time, locale) : "",
                      place: group.resourceName,
                    })}
                    onClick={() => onPick(slot)}
                    className={cn(
                      "min-w-16 rounded-lg border px-2.5 py-1 text-sm tabular-nums transition-colors",
                      isSelected
                        ? "border-accent bg-accent-soft text-accent-ink"
                        : "border-line-strong bg-surface text-ink hover:bg-surface-muted",
                    )}
                  >
                    {slot.time ? formatLocalTime(slot.time, locale) : ""}
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
      <p className="text-xs text-ink-subtle">{t("bookings.form.wholeDayHint")}</p>
    </div>
  );
}
