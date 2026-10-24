/**
 * The answers of /create kept in this browser until the business exists:
 * the name, the niche and its first answers, the country, city, address
 * and languages. A reload (or coming back tomorrow) continues where the
 * owner was; creating the business forgets them. One draft per account,
 * so a shared computer never shows one owner's answers to another.
 *
 * Storage can be missing or refuse (private windows, quotas): every access
 * is wrapped, and a broken or foreign value reads as no draft.
 */

import type { AnswerValues } from "@/lib/wizard/answers";

export const DRAFT_KEY_PREFIX = "aw_create_draft:";
const DRAFT_VERSION = 1;

export interface CreateDraft {
  step: "business" | "place";
  name: string;
  nicheKey: string;
  answers: AnswerValues;
  /** The country chosen, or null to keep suggesting one. */
  countryCode: string | null;
  city: string;
  address: string;
  /** The owner's choices per country, so switching countries back keeps them. */
  languagesByCountry: Record<string, string[]>;
  defaultByCountry: Record<string, string>;
  zoneByCountry: Record<string, string>;
}

export const EMPTY_DRAFT: CreateDraft = {
  step: "business",
  name: "",
  nicheKey: "",
  answers: {},
  countryCode: null,
  city: "",
  address: "",
  languagesByCountry: {},
  defaultByCountry: {},
  zoneByCountry: {},
};

export type DraftStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function draftKey(userId: string): string {
  return `${DRAFT_KEY_PREFIX}${userId}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringRecord(value: unknown): Record<string, string> {
  return isRecord(value)
    ? Object.fromEntries(Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string"))
    : {};
}

function stringListRecord(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) {
    return {};
  }
  const result: Record<string, string[]> = {};
  for (const [key, list] of Object.entries(value)) {
    if (Array.isArray(list) && list.every((item) => typeof item === "string")) {
      result[key] = list;
    }
  }
  return result;
}

function answerValues(value: unknown): AnswerValues {
  if (!isRecord(value)) {
    return {};
  }
  const result: AnswerValues = {};
  for (const [key, answer] of Object.entries(value)) {
    if (isRecord(answer) && typeof answer.text === "string" && Array.isArray(answer.choices)) {
      result[key] = { text: answer.text, choices: answer.choices.filter((choice): choice is string => typeof choice === "string") };
    }
  }
  return result;
}

const text = (value: unknown): string => (typeof value === "string" ? value : "");

/** A stored draft read back field by field; anything unexpected is dropped. */
export function parseDraft(raw: string | null): CreateDraft | null {
  if (!raw) {
    return null;
  }
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(value) || value.version !== DRAFT_VERSION || !isRecord(value.draft)) {
    return null;
  }
  const draft = value.draft;
  return {
    step: draft.step === "place" ? "place" : "business",
    name: text(draft.name),
    nicheKey: text(draft.nicheKey),
    answers: answerValues(draft.answers),
    countryCode: typeof draft.countryCode === "string" && /^[A-Z]{2}$/.test(draft.countryCode) ? draft.countryCode : null,
    city: text(draft.city),
    address: text(draft.address),
    languagesByCountry: stringListRecord(draft.languagesByCountry),
    defaultByCountry: stringRecord(draft.defaultByCountry),
    zoneByCountry: stringRecord(draft.zoneByCountry),
  };
}

export function serializeDraft(draft: CreateDraft): string {
  return JSON.stringify({ version: DRAFT_VERSION, draft });
}

/** True when nothing was typed yet (no reason to keep or restore it). */
export function isDraftEmpty(draft: CreateDraft): boolean {
  return draft.name.trim() === "" && draft.nicheKey === "" && draft.city.trim() === "" && draft.address.trim() === "";
}

export function readDraft(storage: DraftStorage | null, userId: string): CreateDraft | null {
  try {
    return parseDraft(storage?.getItem(draftKey(userId)) ?? null);
  } catch {
    return null;
  }
}

export function writeDraft(storage: DraftStorage | null, userId: string, draft: CreateDraft): boolean {
  try {
    if (!storage) {
      return false;
    }
    if (isDraftEmpty(draft)) {
      storage.removeItem(draftKey(userId));
    } else {
      storage.setItem(draftKey(userId), serializeDraft(draft));
    }
    return true;
  } catch {
    return false;
  }
}

export function clearDraft(storage: DraftStorage | null, userId: string): void {
  try {
    storage?.removeItem(draftKey(userId));
  } catch {
    // Nothing to forget where nothing could be kept.
  }
}

/** The browser's localStorage, or null where reading it throws. */
export function browserStorage(): DraftStorage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}
