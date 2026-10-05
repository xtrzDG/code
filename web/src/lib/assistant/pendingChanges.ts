/**
 * The changes customers do not get yet (GET …/assistant/pending-changes)
 * in the owner's words: one line per change ("Price of “Khachapuri”:
 * 18,00 ₾ → 20,00 ₾"), grouped by the part of the business they touch,
 * and the short summary of the toast once they are live ("Your assistant
 * now knows: …").
 */

import type { Schema } from "@/api/types";
import type { Translator } from "@/i18n/translate";
import { interfaceSentence, joinSentences, type SentenceWithUserValues } from "@/i18n/userValues";
import { formatDate, formatMoney, majorToMinor, weekdayName } from "@/lib/format";

export type PendingChange = Schema<"PendingChange">;
export type PendingChangeArea = Schema<"PendingChangeArea">;
export type PendingChangesView = Schema<"PendingChangesView">;
/** The areas listed as changes; the owner's checks come in a list of their own (`owner_checks`). */
export type ListedArea = Exclude<PendingChangeArea, "owner_checks">;

type Words = Pick<Translator, "t" | "tp" | "tDynamic" | "locale">;

/** The order the areas are listed in (the API sends them in this order too). */
export const AREA_ORDER: readonly ListedArea[] = [
  "profile",
  "hours",
  "special_days",
  "answers",
  "offer",
  "questions",
  "resources",
  "booking_rules",
  "links",
  "languages",
  "calls",
  "conversation",
];

/** The sections of the cabinet's cache what the assistant knows is built from. */
const SOURCE_SECTIONS: ReadonlySet<string> = new Set(["business", "profile", "knowledge", "resources", "billing"]);

/**
 * True when a query key prefix marked out of date (a save, a live event)
 * belongs to one of the business's source sections: the changes not live
 * yet are read again.
 */
export function touchesPendingChanges(prefix: readonly unknown[], businessId: string): boolean {
  const [section, owner] = prefix;
  return typeof section === "string" && SOURCE_SECTIONS.has(section) && (owner === undefined || owner === businessId);
}

/** How many changes the toast names before "and N more". */
export const SUMMARY_LIMIT = 3;

const MONEY_PATTERN = /^(\d+(?:\.\d+)?) ([A-Z]{3})$/;
const LOCAL_DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

/** "18.00 GEL" as the locale writes money ("18,00 ₾"); anything else as it is. */
export function formatPrice(text: string | null | undefined, locale: string): string {
  const [, amount, currency] = MONEY_PATTERN.exec(text ?? "") ?? [];
  if (amount === undefined || currency === undefined) {
    return text ?? "";
  }
  return formatMoney(majorToMinor(Number(amount), currency), currency, locale);
}

function formatLocalDate(date: string | null | undefined, locale: string): string {
  const match = LOCAL_DATE_PATTERN.exec(date ?? "");
  if (!match) {
    return date ?? "";
  }
  const [, year, month, day] = match;
  return formatDate(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))), {
    locale,
    timeZone: "UTC",
    dateStyle: "long",
  });
}

/*
 * The sentences below come as their translation with the owner's own
 * words apart (an item's, answer's or resource's name: `{name}`), so
 * `UserSentence` shows those as user content.
 */

/** What a change is about, as a noun ("“Khachapuri”", "opening hours (Monday)", "address"). */
function changeThing(change: PendingChange, words: Words): SentenceWithUserValues {
  const { t, tDynamic, locale } = words;
  switch (change.area) {
    case "hours":
      return interfaceSentence(t("applyChanges.hours", { weekday: change.weekday ? weekdayName(change.weekday, locale) : "" }));
    case "special_days":
      return interfaceSentence(t("applyChanges.specialDay", { date: formatLocalDate(change.date, locale) }));
    case "links":
      return interfaceSentence(tDynamic(`applyChanges.links.${change.link_kind ?? ""}`, change.link_kind ?? ""));
    case "profile":
    case "booking_rules":
    case "languages":
      return interfaceSentence(tDynamic(`applyChanges.fields.${change.field ?? ""}`, change.field ?? ""));
    case "calls":
    case "conversation":
      return interfaceSentence(t(`applyChanges.areas.${change.area}`));
    default:
      return { text: t("applyChanges.item"), values: { name: change.subject ?? "" } };
  }
}

/** One change as a line of the list ("Changed: address", "Price of “Khachapuri”: 18,00 ₾ → 20,00 ₾"). */
export function describeChange(change: PendingChange, words: Words): SentenceWithUserValues {
  const { t, locale } = words;
  if (change.area === "calls") {
    return interfaceSentence(t(`applyChanges.calls.${change.action}`));
  }
  if (change.area === "conversation") {
    return interfaceSentence(t("applyChanges.conversation"));
  }
  const { text: thing, values } = changeThing(change, words);
  if (change.action === "changed" && change.detail === "price") {
    const before = formatPrice(change.before, locale);
    const after = formatPrice(change.after, locale);
    if (!after) {
      return { text: t("applyChanges.priceRemoved", { item: thing }), values };
    }
    return {
      text: before ? t("applyChanges.price", { item: thing, before, after }) : t("applyChanges.priceSet", { item: thing, after }),
      values,
    };
  }
  if (change.action === "changed" && change.detail === "details") {
    return { text: t("applyChanges.details", { item: thing }), values };
  }
  return { text: t(`applyChanges.actions.${change.action}`, { thing }), values };
}

/** The changes by area, in AREA_ORDER, each area once. */
export function groupChanges(changes: readonly PendingChange[]): { area: ListedArea; changes: PendingChange[] }[] {
  return AREA_ORDER.map((area) => ({ area, changes: changes.filter((change) => change.area === area) })).filter(
    (group) => group.changes.length > 0,
  );
}

/** A change in the toast's list: the new price with its item, otherwise what it is about. */
function shortChange(change: PendingChange, words: Words): SentenceWithUserValues {
  const thing = changeThing(change, words);
  if (change.detail === "price" && change.after) {
    return { text: words.t("applyChanges.priceShort", { item: thing.text, after: formatPrice(change.after, words.locale) }), values: thing.values };
  }
  return thing;
}

/**
 * "Your assistant now knows: “Khachapuri”, 20,00 ₾" for the toast, or null
 * when nothing was added or changed (only removals: the title says enough).
 */
export function summarizeChanges(changes: readonly PendingChange[], words: Words): SentenceWithUserValues | null {
  const known = changes.filter((change) => change.action !== "removed");
  if (known.length === 0) {
    return null;
  }
  const named = known.slice(0, SUMMARY_LIMIT).map((change) => shortChange(change, words));
  const list = joinSentences(named, ", ");
  const rest = known.length - named.length;
  const text = rest > 0 ? words.tp("applyChanges.done.andMore", rest, { changes: list.text }) : list.text;
  return { text: words.t("applyChanges.done.knows", { changes: text }), values: list.values };
}
