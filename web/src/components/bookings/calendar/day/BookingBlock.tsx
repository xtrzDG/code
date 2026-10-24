"use client";

import type { CSSProperties, ComponentProps } from "react";

import { BOOKING_STATUS } from "@/components/insights/labels";
import { formatLocalTime } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";
import type { PartyWording } from "@/components/insights/usePartyWording";
import { UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { Laned } from "../_lib/dayLayout";
import { GHOST_CLASS, STATUS_STYLE } from "../calendarStyles";
import { MINUTE_HEIGHT } from "./dayLocate";

/** The block's place on its column: its time from top to bottom, its lane across. */
function blockStyle(laned: Pick<Laned<unknown>, "span" | "lane" | "lanes">, axisStart: number): CSSProperties {
  const top = (laned.span.start - axisStart) * MINUTE_HEIGHT;
  const height = Math.max((laned.span.end - laned.span.start) * MINUTE_HEIGHT, 22);
  return {
    top: top + 1,
    height: height - 2,
    insetInlineStart: `calc(${(laned.lane / laned.lanes) * 100}% + 3px)`,
    width: `calc(${100 / laned.lanes}% - 6px)`,
  };
}

function useBlockTexts(booking: BookingView, party: PartyWording | null) {
  const { t, locale } = useI18n();
  const times = [booking.time, booking.end_time].filter(Boolean).map((time) => formatLocalTime(time ?? "", locale));
  const name = booking.contact_name ?? t("insights.unknownCustomer");
  const partyText = party ? party.count(booking.party_size, booking.resource_id) : null;
  return {
    name,
    times: times.join("–"),
    details: [partyText, booking.service_title].filter(Boolean).join(" · "),
    label: t("bookingCalendar.block.label", {
      name,
      time: times.join("–"),
      place: booking.resource_name,
      status: t(BOOKING_STATUS[booking.status].label),
    }),
  };
}

/**
 * A booking on the day grid, coloured by its status: the time, who, and
 * (when tall enough) how many and what for. A button: Enter or a click
 * opens it; dragging it, or the arrow keys, move it (useMoveGestures).
 */
export function BookingBlock({
  laned,
  axisStart,
  hintId,
  party,
  isMoving,
  onOpen,
  movable,
}: {
  laned: Laned<BookingView>;
  axisStart: number;
  hintId: string;
  party: PartyWording;
  /** Its preview is elsewhere: the block stays as a faint trace. */
  isMoving: boolean;
  onOpen: (booking: BookingView) => void;
  movable: Partial<ComponentProps<"button">>;
}) {
  const { t } = useI18n();
  const booking = laned.item;
  const texts = useBlockTexts(booking, party);
  const minutes = laned.span.end - laned.span.start;
  // Side by side with others, a block shows when it starts; its end is in its label and on the grid.
  const shownTimes = laned.lanes > 1 ? texts.times.split("–")[0] : texts.times;
  return (
    <button
      type="button"
      {...movable}
      onClick={() => onOpen(booking)}
      aria-label={texts.label}
      aria-describedby={hintId}
      style={blockStyle(laned, axisStart)}
      className={cn(
        "group/block absolute z-10 flex cursor-grab flex-col overflow-hidden rounded-lg border ps-3 pe-1.5 py-1 text-start text-xs leading-tight shadow-sm",
        "touch-pan-x touch-pan-y select-none [-webkit-touch-callout:none] active:cursor-grabbing",
        "transition-[opacity,box-shadow] duration-150 hover:shadow-md focus-visible:z-20 focus-visible:outline-2 focus-visible:-outline-offset-1",
        STATUS_STYLE[booking.status].block,
        isMoving && "opacity-40",
      )}
    >
      <span aria-hidden className={cn("absolute inset-y-1 start-1 w-1 rounded-full", STATUS_STYLE[booking.status].mark)} />
      <span className="flex min-w-0 items-baseline gap-1.5">
        <span className="shrink-0 font-medium text-ink-muted tabular-nums">{shownTimes}</span>
        {minutes < 45 ? <UserContent className="truncate font-semibold text-ink">{texts.name}</UserContent> : null}
        {booking.is_sandbox ? (
          <span className="ms-auto shrink-0 rounded bg-surface px-1 text-[10px] font-semibold text-ink-subtle uppercase">
            {t("bookingCalendar.block.test")}
          </span>
        ) : null}
      </span>
      {minutes >= 45 ? <UserContent className="truncate font-semibold text-ink">{texts.name}</UserContent> : null}
      {minutes >= 75 && texts.details ? <span className="truncate text-ink-muted">{texts.details}</span> : null}
    </button>
  );
}

/** Where the dragged (or keyboard-moved) booking would land, drawn on its target column. */
export function BlockGhost({ laned, axisStart }: { laned: Laned<BookingView>; axisStart: number }) {
  const texts = useBlockTexts(laned.item, null);
  return (
    <div
      aria-hidden
      data-calendar-ghost=""
      style={{ ...blockStyle({ ...laned, lane: 0, lanes: 1 }, axisStart), zIndex: 30 }}
      className={cn("absolute flex flex-col overflow-hidden rounded-lg px-2 py-1 text-xs leading-tight shadow-lg", GHOST_CLASS)}
    >
      <span className="font-semibold tabular-nums">{texts.times}</span>
      <UserContent className="truncate">{texts.name}</UserContent>
    </div>
  );
}
