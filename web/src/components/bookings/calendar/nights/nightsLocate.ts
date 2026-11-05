/**
 * Where a stay dragged on the nights grid would land: the room row under
 * (or nearest to) the pointer, and the night its first night would take,
 * keeping the night that was grabbed under the pointer.
 */

import type { PointerEvent } from "react";

import { addDays, daysBetween } from "@/components/insights/dates";
import type { BookingView } from "@/components/insights/types";

import type { Locate } from "../useMoveGestures";

/** The nearest of the elements matching `selector` along one axis, with its rectangle. */
function nearest(container: HTMLElement | null, selector: string, at: number, axis: "x" | "y"): HTMLElement | null {
  let best: HTMLElement | null = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  for (const element of container?.querySelectorAll<HTMLElement>(selector) ?? []) {
    const rect = element.getBoundingClientRect();
    const [low, high] = axis === "x" ? [rect.left, rect.right] : [rect.top, rect.bottom];
    const distance = at < low ? low - at : at > high ? at - high : 0;
    if (distance < bestDistance) {
      bestDistance = distance;
      best = element;
    }
  }
  return best;
}

/** The index (in the window) of the night under `x`. */
function nightAt(container: HTMLElement | null, x: number): number | null {
  const cell = nearest(container, "[data-night-index]", x, "x");
  return cell ? Number(cell.dataset.nightIndex) : null;
}

/** The locator of a stay grabbed on the nights grid. */
export function nightsLocator(container: () => HTMLElement | null, booking: BookingView, from: string): (event: PointerEvent<HTMLElement>) => Locate {
  return (event) => {
    const start = daysBetween(from, booking.date);
    const grabbed = nightAt(container(), event.clientX) ?? start;
    return (x, y) => {
      const night = nightAt(container(), x);
      const room = nearest(container(), "[data-calendar-room]", y, "y");
      if (night === null || !room) {
        return null;
      }
      return {
        resourceId: room.dataset.calendarRoom ?? booking.resource_id,
        resourceName: room.dataset.placeName ?? booking.resource_name,
        date: addDays(from, night - (grabbed - start)),
        time: null,
      };
    };
  };
}
