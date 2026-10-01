/**
 * Pure helpers of the Knowledge section (app/b/[businessId]/knowledge):
 * kinds and grouping, the item form and its API bodies, menu-import drafts.
 *
 * Prices are typed in major units ("18,50") and sent in minor units of the
 * business currency (1850).
 */

import type { KnowledgeItemDetails, KnowledgeItemKind, RequestBody, Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import {
  currencyFractionDigits,
  decimalInputValue,
  majorToMinor,
  minorToMajor,
  parseDecimalInput,
} from "./format";

export type KnowledgeItemCreateBody = RequestBody<"/v1/businesses/{business_id}/knowledge", "post">;
export type KnowledgeItemPatchBody = RequestBody<"/v1/businesses/{business_id}/knowledge/{item_id}", "patch">;
export type ImportedMenuItem = Schema<"ImportedMenuItemView">;

/** Every kind, in the order the API lists them. */
export const KNOWLEDGE_KINDS: readonly KnowledgeItemKind[] = [
  "menu_item",
  "service",
  "room_type",
  "package",
  "vehicle",
  "product",
  "faq",
  "policy",
];

export const MAX_TITLE_LENGTH = 300;
export const MAX_BODY_LENGTH = 8000;
export const MAX_DURATION_MINUTES = 43_200;

/** The niche's kinds first (in its order), then every other kind. */
export function orderKinds(nicheKinds: readonly KnowledgeItemKind[] | undefined): KnowledgeItemKind[] {
  const first = (nicheKinds ?? []).filter((kind, index, list) => list.indexOf(kind) === index);
  return [...first, ...KNOWLEDGE_KINDS.filter((kind) => !first.includes(kind))];
}

/** Questions and rules have no price; everything sold does. */
export function kindHasPrice(kind: KnowledgeItemKind): boolean {
  return kind !== "faq" && kind !== "policy";
}

/** Kinds that usually last a while (a haircut, a VR hour, a car for a day). */
export function kindHasDuration(kind: KnowledgeItemKind): boolean {
  return kind === "service" || kind === "package" || kind === "vehicle";
}

export type KnowledgeStatusFilter = "all" | "active" | "inactive";

export interface KnowledgeFilter {
  kind: KnowledgeItemKind | "all";
  status: KnowledgeStatusFilter;
}

export function filterKnowledgeItems<T extends Pick<KnowledgeItemDetails, "kind" | "is_active">>(
  items: readonly T[],
  filter: KnowledgeFilter,
): T[] {
  return items.filter(
    (item) =>
      (filter.kind === "all" || item.kind === filter.kind) &&
      (filter.status === "all" || (filter.status === "active") === item.is_active),
  );
}

export interface KnowledgeGroup<T> {
  kind: KnowledgeItemKind;
  items: T[];
}

/** Non-empty groups in `kindOrder`; items keep their order inside a group. */
export function groupByKind<T extends Pick<KnowledgeItemDetails, "kind">>(
  items: readonly T[],
  kindOrder: readonly KnowledgeItemKind[],
): KnowledgeGroup<T>[] {
  const order = [...kindOrder, ...KNOWLEDGE_KINDS.filter((kind) => !kindOrder.includes(kind))];
  const groups = new Map<KnowledgeItemKind, T[]>();
  for (const item of items) {
    const list = groups.get(item.kind) ?? [];
    list.push(item);
    groups.set(item.kind, list);
  }
  return order.flatMap((kind) => {
    const list = groups.get(kind);
    return list && list.length > 0 ? [{ kind, items: list }] : [];
  });
}

/** Items by title in the UI language (the API's order), e.g. after adding one locally. */
export function sortByTitle<T extends Pick<KnowledgeItemDetails, "title">>(items: readonly T[], locale: string): T[] {
  return [...items].sort((left, right) => left.title.localeCompare(right.title, locale, { sensitivity: "base" }));
}

export function countByKind(items: readonly Pick<KnowledgeItemDetails, "kind">[]): Partial<Record<KnowledgeItemKind, number>> {
  const counts: Partial<Record<KnowledgeItemKind, number>> = {};
  for (const item of items) {
    counts[item.kind] = (counts[item.kind] ?? 0) + 1;
  }
  return counts;
}

// --- The item form -------------------------------------------------------------

/** The editor's values; price and duration are kept as typed. */
export interface KnowledgeForm {
  kind: KnowledgeItemKind;
  title: string;
  body: string;
  price: string;
  duration: string;
  languages: string[];
  isActive: boolean;
}

export type KnowledgeFormErrors = Partial<Record<"title" | "body" | "price" | "duration", MessageKey>>;

export function emptyKnowledgeForm(kind: KnowledgeItemKind): KnowledgeForm {
  return { kind, title: "", body: "", price: "", duration: "", languages: [], isActive: true };
}

type FormSource = Pick<KnowledgeItemDetails, "kind" | "title" | "body" | "price_minor" | "duration_minutes"> &
  Partial<Pick<KnowledgeItemDetails, "languages" | "is_active">>;

export function knowledgeFormFromItem(item: FormSource, currency: string): KnowledgeForm {
  return {
    kind: item.kind,
    title: item.title,
    body: item.body ?? "",
    price:
      item.price_minor === null || item.price_minor === undefined
        ? ""
        : decimalInputValue(minorToMajor(item.price_minor, currency), currencyFractionDigits(currency)),
    duration: item.duration_minutes ? String(item.duration_minutes) : "",
    languages: [...(item.languages ?? [])],
    isActive: item.is_active ?? true,
  };
}

function decimalPlaces(text: string): number {
  const compact = text.replace(/[\s  ']/g, "");
  const separator = Math.max(compact.lastIndexOf(","), compact.lastIndexOf("."));
  if (separator < 0) {
    return 0;
  }
  // "1,200" or "1.200.000" are groupings, not decimals: parseDecimalInput agrees.
  const parsed = parseDecimalInput(compact);
  if (parsed === null || Number.isInteger(parsed)) {
    return 0;
  }
  return compact.length - separator - 1;
}

export function validateKnowledgeForm(form: KnowledgeForm, currency: string): KnowledgeFormErrors {
  const errors: KnowledgeFormErrors = {};
  const title = form.title.trim();
  const body = form.body.trim();
  if (title === "") {
    errors.title = "validation.required";
  } else if (title.length > MAX_TITLE_LENGTH) {
    errors.title = "validation.tooLong";
  }
  if (form.kind === "faq" && body === "") {
    errors.body = "validation.required";
  } else if (body.length > MAX_BODY_LENGTH) {
    errors.body = "validation.tooLong";
  }
  if (kindHasPrice(form.kind) && form.price.trim() !== "") {
    if (parseDecimalInput(form.price) === null) {
      errors.price = "validation.number";
    } else if (decimalPlaces(form.price) > currencyFractionDigits(currency)) {
      errors.price = "knowledge.form.priceTooPrecise";
    }
  }
  const duration = form.duration.trim();
  if (duration !== "") {
    if (!/^\d+$/.test(duration)) {
      errors.duration = "validation.wholeNumber";
    } else if (Number(duration) < 1 || Number(duration) > MAX_DURATION_MINUTES) {
      errors.duration = "validation.positive";
    }
  }
  return errors;
}

function priceMinor(form: KnowledgeForm, currency: string): number | null {
  if (!kindHasPrice(form.kind)) {
    return null;
  }
  const price = parseDecimalInput(form.price);
  return price === null ? null : majorToMinor(price, currency);
}

function durationMinutes(form: KnowledgeForm): number | null {
  const duration = form.duration.trim();
  return duration === "" ? null : Number(duration);
}

/** Body of POST …/knowledge for a validated form. */
export function knowledgeCreateBody(form: KnowledgeForm, currency: string): KnowledgeItemCreateBody {
  return {
    kind: form.kind,
    title: form.title.trim(),
    body: form.body.trim() || null,
    price_minor: priceMinor(form, currency),
    duration_minutes: durationMinutes(form),
    languages: form.languages,
    is_active: form.isActive,
  };
}

function sameLanguages(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && [...left].sort().join(",") === [...right].sort().join(",");
}

/**
 * Body of PATCH …/knowledge/{id}: only what changed against `initial`
 * (an explicit null clears body, price or duration). Empty when nothing changed.
 */
export function knowledgePatchBody(form: KnowledgeForm, initial: KnowledgeForm, currency: string): KnowledgeItemPatchBody {
  const patch: KnowledgeItemPatchBody = {};
  if (form.kind !== initial.kind) {
    patch.kind = form.kind;
  }
  if (form.title.trim() !== initial.title.trim()) {
    patch.title = form.title.trim();
  }
  if (form.body.trim() !== initial.body.trim()) {
    patch.body = form.body.trim() || null;
  }
  const price = priceMinor(form, currency);
  if (price !== priceMinor(initial, currency)) {
    patch.price_minor = price;
  }
  const duration = durationMinutes(form);
  if (duration !== durationMinutes(initial)) {
    patch.duration_minutes = duration;
  }
  if (!sameLanguages(form.languages, initial.languages)) {
    patch.languages = form.languages;
  }
  if (form.isActive !== initial.isActive) {
    patch.is_active = form.isActive;
  }
  return patch;
}

export function isEmptyPatch(patch: KnowledgeItemPatchBody): boolean {
  return Object.keys(patch).length === 0;
}

// --- Menu import ----------------------------------------------------------------

export type ConfidenceLevel = "high" | "medium" | "low";

/** How sure the reader was about a line: ≥ 0.8 high, ≥ 0.5 medium, else low. */
export function confidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.8) {
    return "high";
  }
  return confidence >= 0.5 ? "medium" : "low";
}

/** Drafts checked at first: everything the reader was at least fairly sure of. */
export function initialImportSelection(items: readonly ImportedMenuItem[]): Set<string> {
  return new Set(items.filter((item) => confidenceLevel(item.confidence) !== "low").map((item) => item.item.id));
}

/** The largest file the API takes (15 MB, sent as base64). */
export const MENU_UPLOAD_MAX_BYTES = 15 * 1024 * 1024;

const MEDIA_TYPES_BY_EXTENSION: Record<string, string> = {
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  png: "image/png",
  webp: "image/webp",
  gif: "image/gif",
  pdf: "application/pdf",
  txt: "text/plain",
  csv: "text/csv",
  htm: "text/html",
  html: "text/html",
};

/** Media types the menu reader accepts for uploads. */
export const MENU_UPLOAD_MEDIA_TYPES: readonly string[] = [...new Set(Object.values(MEDIA_TYPES_BY_EXTENSION))];

/** `accept` of the file input. */
export const MENU_UPLOAD_ACCEPT = [...MENU_UPLOAD_MEDIA_TYPES, ...Object.keys(MEDIA_TYPES_BY_EXTENSION).map((ext) => `.${ext}`)].join(",");

/**
 * The media type to send for a chosen file: the browser's type when the
 * reader accepts it, else one from the extension (browsers often leave
 * .csv or .txt untyped). Null for unsupported files.
 */
export function menuMediaType(fileName: string, browserType: string): string | null {
  const type = browserType.trim().toLowerCase().split(";")[0] ?? "";
  if (type === "image/jpg" || type === "image/pjpeg") {
    return "image/jpeg";
  }
  if (MENU_UPLOAD_MEDIA_TYPES.includes(type)) {
    return type;
  }
  const extension = /\.([a-z0-9]+)$/i.exec(fileName.trim())?.[1]?.toLowerCase();
  return extension ? (MEDIA_TYPES_BY_EXTENSION[extension] ?? null) : null;
}

export type MenuFileCheck = { ok: true; mediaType: string } | { ok: false; error: MessageKey };

export function checkMenuFile(file: { name: string; type: string; size: number }): MenuFileCheck {
  const mediaType = menuMediaType(file.name, file.type);
  if (mediaType === null) {
    return { ok: false, error: "knowledge.import.errors.fileType" };
  }
  if (file.size === 0) {
    return { ok: false, error: "knowledge.import.errors.fileEmpty" };
  }
  if (file.size > MENU_UPLOAD_MAX_BYTES) {
    return { ok: false, error: "knowledge.import.errors.fileTooLarge" };
  }
  return { ok: true, mediaType };
}

/** "data:image/png;base64,AAAA" -> "AAAA". */
export function base64FromDataUrl(dataUrl: string): string {
  const comma = dataUrl.indexOf(",");
  return comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
}

/** A file size for people: 1536 -> "1.5 KB" (decimal separator from the locale). */
export function formatFileSize(bytes: number, locale: string): string {
  const units = ["B", "KB", "MB"] as const;
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: unit === 0 ? 0 : 1 }).format(value);
  return `${number} ${units[unit]}`;
}
