/**
 * The platform team's announcements for the status page and the cabinet's
 * banner (POST and PATCH /v1/admin/announcements): the form as typed, its
 * checks and the request bodies. English is required; Georgian and Russian
 * are either a text or empty (owners then read English). Pure functions, so
 * the dialog and the tests share them.
 */

import type { RequestBody, Schema } from "@/api/types";

import { localInputToMicros, microsToLocalInput } from "./incidentForm";

export type AdminAnnouncement = Schema<"AnnouncementAdminView">;
export type AnnouncementLevel = Schema<"AnnouncementLevel">;
export type StatusComponent = Schema<"StatusComponent">;
export type CreateAnnouncementBody = RequestBody<"/v1/admin/announcements", "post">;
export type UpdateAnnouncementBody = RequestBody<"/v1/admin/announcements/{announcement_id}", "patch">;

export const ANNOUNCEMENT_LANGUAGES = ["en", "ka", "ru"] as const;
export type AnnouncementLanguage = (typeof ANNOUNCEMENT_LANGUAGES)[number];

/** The API's limits. */
export const TEXT_MIN_LENGTH = 3;
export const TEXT_MAX_LENGTH = 600;
const MAX_LEAD_MICROS = 60 * 24 * 60 * 60 * 1_000_000;

export interface AnnouncementForm {
  level: AnnouncementLevel;
  components: StatusComponent[];
  texts: Record<AnnouncementLanguage, string>;
  /** `<input type="datetime-local">`; empty: now. Fixed once published. */
  startsAt: string;
  /** Empty: no expected end. */
  expectedEnd: string;
}

export type AnnouncementProblem = "textRequired" | "textShort" | "componentsRequired" | "time" | "endBeforeStart" | "startTooLate";

export interface AnnouncementErrors {
  texts: Partial<Record<AnnouncementLanguage, AnnouncementProblem>>;
  components?: AnnouncementProblem;
  startsAt?: AnnouncementProblem;
  expectedEnd?: AnnouncementProblem;
}

export const NO_ERRORS: AnnouncementErrors = { texts: {} };

export function emptyAnnouncementForm(): AnnouncementForm {
  return { level: "degraded", components: [], texts: { en: "", ka: "", ru: "" }, startsAt: "", expectedEnd: "" };
}

/** The form of a published announcement, to update it. */
export function formFromAnnouncement(announcement: AdminAnnouncement): AnnouncementForm {
  const texts = { en: "", ka: "", ru: "" };
  for (const message of announcement.messages) {
    if ((ANNOUNCEMENT_LANGUAGES as readonly string[]).includes(message.language)) {
      texts[message.language as AnnouncementLanguage] = message.text;
    }
  }
  return {
    level: announcement.level,
    components: [...announcement.components],
    texts,
    startsAt: microsToLocalInput(announcement.starts_at),
    expectedEnd: announcement.expected_end_at ? microsToLocalInput(announcement.expected_end_at) : "",
  };
}

/** One line, no spaces around it: what the API stores. */
export function cleanText(text: string): string {
  return text.replace(/\s+/g, " ").trim();
}

/** A notice names no part of the platform; every other level names at least one. */
export function needsComponents(level: AnnouncementLevel): boolean {
  return level !== "info";
}

function hasErrors(errors: AnnouncementErrors): boolean {
  return Object.keys(errors.texts).length > 0 || Boolean(errors.components || errors.startsAt || errors.expectedEnd);
}

interface Checked {
  errors: AnnouncementErrors;
  messages: { language: AnnouncementLanguage; text: string }[];
  components: StatusComponent[];
  startsAt: number | null;
  expectedEnd: number | null;
}

function check(form: AnnouncementForm, nowMicros: number, isNew: boolean): Checked {
  const errors: AnnouncementErrors = { texts: {} };
  const messages: Checked["messages"] = [];
  for (const language of ANNOUNCEMENT_LANGUAGES) {
    const text = cleanText(form.texts[language]);
    if (text.length >= TEXT_MIN_LENGTH) {
      messages.push({ language, text });
    } else if (language === "en") {
      errors.texts.en = "textRequired";
    } else if (text.length > 0) {
      errors.texts[language] = "textShort";
    }
  }
  const components = needsComponents(form.level) ? form.components : [];
  if (needsComponents(form.level) && components.length === 0) {
    errors.components = "componentsRequired";
  }

  const startsAt = isNew && form.startsAt.trim() ? localInputToMicros(form.startsAt) : null;
  if (isNew && form.startsAt.trim() && startsAt === null) {
    errors.startsAt = "time";
  } else if (startsAt !== null && startsAt > nowMicros + MAX_LEAD_MICROS) {
    errors.startsAt = "startTooLate";
  }
  const expectedEnd = form.expectedEnd.trim() ? localInputToMicros(form.expectedEnd) : null;
  const start = isNew ? (startsAt ?? nowMicros) : (localInputToMicros(form.startsAt) ?? nowMicros);
  if (form.expectedEnd.trim() && expectedEnd === null) {
    errors.expectedEnd = "time";
  } else if (expectedEnd !== null && expectedEnd <= Math.max(start, nowMicros)) {
    errors.expectedEnd = "endBeforeStart";
  }
  return { errors, messages, components, startsAt, expectedEnd };
}

export type Built<T> = { ok: true; body: T } | { ok: false; errors: AnnouncementErrors };

export function buildCreateBody(form: AnnouncementForm, nowMicros: number): Built<CreateAnnouncementBody> {
  const checked = check(form, nowMicros, true);
  if (hasErrors(checked.errors)) {
    return { ok: false, errors: checked.errors };
  }
  return {
    ok: true,
    body: {
      level: form.level,
      components: checked.components,
      messages: checked.messages,
      starts_at: checked.startsAt,
      expected_end_at: checked.expectedEnd,
    },
  };
}

const sameList = <T>(left: readonly T[], right: readonly T[]) =>
  left.length === right.length && left.every((item) => right.includes(item));

/** Only what changed; `body: null` when nothing did. */
export function buildUpdateBody(
  form: AnnouncementForm,
  original: AdminAnnouncement,
  nowMicros: number,
): Built<UpdateAnnouncementBody | null> {
  const checked = check(form, nowMicros, false);
  const endChanged = checked.expectedEnd !== null && checked.expectedEnd !== original.expected_end_at;
  if (!endChanged) {
    delete checked.errors.expectedEnd;
  }
  if (hasErrors(checked.errors)) {
    return { ok: false, errors: checked.errors };
  }
  const body: UpdateAnnouncementBody = {};
  if (form.level !== original.level) {
    body.level = form.level;
  }
  if (!sameList(checked.components, original.components)) {
    body.components = checked.components;
  }
  const stored = original.messages.map((message) => `${message.language}\n${message.text}`);
  if (!sameList(checked.messages.map((message) => `${message.language}\n${message.text}`), stored)) {
    body.messages = checked.messages;
  }
  if (endChanged) {
    body.expected_end_at = checked.expectedEnd;
  }
  return { ok: true, body: Object.keys(body).length > 0 ? body : null };
}
