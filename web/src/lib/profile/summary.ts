/**
 * What the cards of Assistant → Business profile say about each section at
 * a glance: the week in a line ("Mon–Fri 10:00–23:00 · Sat 11:00–00:00"),
 * how many things are on offer and with a price, how many ready answers.
 */

import type { KnowledgeItemDetails, OpeningInterval, Weekday } from "@/api/types";

import { formatMinutesOfDay, weekdayName } from "../format";
import { intervalsToWeek, isRoundTheClock, type EditorInterval } from "../hours";
import { isOfferItem } from "../tunnel/offer";

export interface DayGroup {
  /** The first and last weekday of a run of days with the same hours. */
  from: Weekday;
  to: Weekday;
  intervals: EditorInterval[];
}

function sameIntervals(left: readonly EditorInterval[], right: readonly EditorInterval[]): boolean {
  return left.length === right.length && left.every((interval, index) => interval.opens === right[index]?.opens && interval.closes === right[index]?.closes);
}

/** Open days, Monday first, with neighbouring days of the same hours run together. */
export function groupWeek(hours: readonly OpeningInterval[]): DayGroup[] {
  const groups: DayGroup[] = [];
  for (const day of intervalsToWeek(hours)) {
    if (day.intervals.length === 0) {
      continue;
    }
    const last = groups.at(-1);
    if (last && last.to === day.weekday - 1 && sameIntervals(last.intervals, day.intervals)) {
      last.to = day.weekday;
    } else {
      groups.push({ from: day.weekday, to: day.weekday, intervals: day.intervals });
    }
  }
  return groups;
}

function intervalText(interval: EditorInterval, roundTheClock: string): string {
  return isRoundTheClock(interval) ? roundTheClock : `${formatMinutesOfDay(interval.opens)}–${formatMinutesOfDay(interval.closes)}`;
}

/**
 * The week in one line in the interface language: "Mon–Fri 10:00–23:00 ·
 * Sat 11:00–15:00, 16:00–00:00"; empty when the business is never open.
 */
export function weekSummary(hours: readonly OpeningInterval[], locale: string, roundTheClock: string): string {
  return groupWeek(hours)
    .map((group) => {
      const days =
        group.from === group.to
          ? weekdayName(group.from, locale, "short")
          : `${weekdayName(group.from, locale, "short")}–${weekdayName(group.to, locale, "short")}`;
      return `${days} ${group.intervals.map((interval) => intervalText(interval, roundTheClock)).join(", ")}`;
    })
    .join(" · ");
}

export interface KnowledgeCounts {
  /** Active things the business sells (dishes, services, rooms…). */
  offers: number;
  /** Of those, the ones with a price. */
  priced: number;
  /** Active frequent questions with their answers. */
  questions: number;
}

export function knowledgeCounts(items: readonly Pick<KnowledgeItemDetails, "kind" | "is_active" | "price_minor">[]): KnowledgeCounts {
  const offers = items.filter(isOfferItem);
  return {
    offers: offers.length,
    priced: offers.filter((item) => item.price_minor !== null && item.price_minor !== undefined).length,
    questions: items.filter((item) => item.kind === "faq" && item.is_active).length,
  };
}
