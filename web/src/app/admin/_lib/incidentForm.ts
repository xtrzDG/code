/**
 * Recording an incident (POST /v1/admin/incidents): the form as typed, its
 * checks, and the request body. A personal data breach carries the DPA 12.1
 * notice: the approximate numbers concerned and the five texts in English
 * (required) and in Georgian and Russian (each either complete or empty).
 * An incident names its businesses or concerns every business (the worker
 * walks them), and may publish its status announcement at once. Pure
 * functions, so the dialog and the tests share them.
 */

import type { RequestBody, Schema } from "@/api/types";

import { buildCreateBody, emptyAnnouncementForm, type AnnouncementErrors, type AnnouncementForm } from "./announcementForm";
import { localInputToMicros, microsToLocalInput } from "./localTime";

export type Incident = Schema<"IncidentView">;
export type IncidentKind = Schema<"IncidentKind">;
export type IncidentSeverity = Schema<"IncidentSeverity">;
type IncidentScope = Schema<"IncidentScope">;
export type CreateIncidentBody = RequestBody<"/v1/admin/incidents", "post">;

export const INCIDENT_KINDS: readonly IncidentKind[] = ["outage", "degradation", "data_breach"];
export const INCIDENT_SEVERITIES: readonly IncidentSeverity[] = ["sev1", "sev2", "sev3"];

/** The languages owners read a notice in; English is the fallback every notice needs. */
export const NOTICE_LANGUAGES = ["en", "ka", "ru"] as const;
export type NoticeLanguage = (typeof NOTICE_LANGUAGES)[number];

export const NOTICE_FIELDS = ["nature", "subject_categories", "record_categories", "likely_consequences", "measures"] as const;
export type NoticeField = (typeof NOTICE_FIELDS)[number];
export type NoticeTexts = Record<NoticeField, string>;

/** The API's limits of each notice text. */
export const NOTICE_MAX_LENGTH: Readonly<Record<NoticeField, number>> = {
  nature: 2000,
  subject_categories: 1000,
  record_categories: 1000,
  likely_consequences: 2000,
  measures: 2000,
};

const TITLE_MIN_LENGTH = 3;
export const TITLE_MAX_LENGTH = 160;
const MAX_AFFECTED_BUSINESSES = 1000;
const MAX_AFFECTED_COUNT = 1_000_000_000;

const BUSINESS_ID = /business_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

export interface IncidentForm {
  kind: IncidentKind;
  severity: IncidentSeverity;
  title: string;
  /** `<input type="datetime-local">` values, in the admin's own time zone. */
  startedAt: string;
  /** Empty: when the incident is recorded. */
  detectedAt: string;
  /** LISTED: the businesses below; ALL_BUSINESSES: every one (the worker walks them). */
  scope: IncidentScope;
  /** Business ids or links to their client pages, one per line or separated by commas. */
  businesses: string;
  subjectCount: string;
  recordCount: string;
  notices: Record<NoticeLanguage, NoticeTexts>;
  /** Also publish a status announcement (it starts now and is linked to the incident). */
  announce: boolean;
  announcement: AnnouncementForm;
}

type IncidentField = "title" | "startedAt" | "detectedAt" | "businesses" | "subjectCount" | "recordCount";

export type IncidentProblem =
  | "required"
  | "title"
  | "future"
  | "order"
  | "businessIds"
  | "tooManyBusinesses"
  | "count"
  | "noticeRequired"
  | "noticeIncomplete";

export interface IncidentFormErrors {
  fields: Partial<Record<IncidentField, IncidentProblem>>;
  notices: Partial<Record<NoticeLanguage, IncidentProblem>>;
  /** What in the businesses field is not a business id. */
  unknownBusinesses: string[];
  /** The announcement's problems, when one is published with the incident. */
  announcement?: AnnouncementErrors;
}

export type BuiltIncident = { ok: true; body: CreateIncidentBody } | { ok: false; errors: IncidentFormErrors };

function emptyNotice(): NoticeTexts {
  return { nature: "", subject_categories: "", record_categories: "", likely_consequences: "", measures: "" };
}

export function emptyIncidentForm(nowMicros: number): IncidentForm {
  return {
    kind: "outage",
    severity: "sev2",
    title: "",
    startedAt: microsToLocalInput(nowMicros),
    detectedAt: "",
    scope: "listed",
    businesses: "",
    subjectCount: "",
    recordCount: "",
    notices: { en: emptyNotice(), ka: emptyNotice(), ru: emptyNotice() },
    announce: false,
    announcement: { ...emptyAnnouncementForm(), level: "outage", components: ["chat", "meta", "telegram"] },
  };
}

/**
 * A breach is always SEV1 (docs/operations/incident.md) and is told to the
 * owners, not on the status page; an outage or a degradation is offered the
 * announcement of its level.
 */
export function withKind(form: IncidentForm, kind: IncidentKind): IncidentForm {
  const isBreach = kind === "data_breach";
  return {
    ...form,
    kind,
    severity: isBreach ? "sev1" : form.severity,
    announce: isBreach ? false : form.announce,
    announcement: { ...form.announcement, level: kind === "degradation" ? "degraded" : "outage" },
  };
}

/** Offering the announcement: its English text starts as the incident's title. */
export function withAnnouncement(form: IncidentForm, announce: boolean): IncidentForm {
  const texts = form.announcement.texts;
  const english = texts.en.trim() ? texts.en : form.title.trim();
  return { ...form, announce, announcement: { ...form.announcement, texts: { ...texts, en: english } } };
}

/** Business ids found in pasted text (ids or client page links), each once, and what is neither. */
export function parseBusinessIds(text: string): { ids: string[]; unknown: string[] } {
  const ids: string[] = [];
  const unknown: string[] = [];
  for (const token of text.split(/[\s,;]+/)) {
    if (!token) {
      continue;
    }
    const match = BUSINESS_ID.exec(token);
    if (!match) {
      unknown.push(token);
      continue;
    }
    const id = match[0].toLowerCase();
    if (!ids.includes(id)) {
      ids.push(id);
    }
  }
  return { ids, unknown };
}

function parseCount(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const value = Number(trimmed);
  return value <= MAX_AFFECTED_COUNT ? value : null;
}

/** "complete": all five texts; "empty": none; "partial": some. */
export function noticeFill(notice: NoticeTexts): "complete" | "empty" | "partial" {
  const filled = NOTICE_FIELDS.filter((field) => notice[field].trim() !== "").length;
  return filled === NOTICE_FIELDS.length ? "complete" : filled === 0 ? "empty" : "partial";
}

function checkTimes(form: IncidentForm, nowMicros: number, fields: IncidentFormErrors["fields"]) {
  const startedAt = localInputToMicros(form.startedAt);
  const detectedAt = form.detectedAt.trim() ? localInputToMicros(form.detectedAt) : null;
  if (startedAt === null) {
    fields.startedAt = "required";
  } else if (startedAt > nowMicros) {
    fields.startedAt = "future";
  }
  if (form.detectedAt.trim() && detectedAt === null) {
    fields.detectedAt = "required";
  } else if (detectedAt !== null && detectedAt > nowMicros) {
    fields.detectedAt = "future";
  } else if (detectedAt !== null && startedAt !== null && !fields.startedAt && detectedAt < startedAt) {
    fields.detectedAt = "order";
  }
  return { startedAt, detectedAt };
}

function checkBreach(form: IncidentForm, errors: IncidentFormErrors) {
  const subjects = parseCount(form.subjectCount);
  const records = parseCount(form.recordCount);
  if (subjects === null) {
    errors.fields.subjectCount = form.subjectCount.trim() ? "count" : "required";
  }
  if (records === null) {
    errors.fields.recordCount = form.recordCount.trim() ? "count" : "required";
  }
  for (const language of NOTICE_LANGUAGES) {
    const fill = noticeFill(form.notices[language]);
    if (fill === "partial") {
      errors.notices[language] = "noticeIncomplete";
    } else if (fill === "empty" && language === "en") {
      errors.notices[language] = "noticeRequired";
    }
  }
  const noticeTexts = NOTICE_LANGUAGES.filter((language) => noticeFill(form.notices[language]) === "complete").map(
    (language) => {
      const notice = form.notices[language];
      return {
        language,
        nature: notice.nature.trim(),
        subject_categories: notice.subject_categories.trim(),
        record_categories: notice.record_categories.trim(),
        likely_consequences: notice.likely_consequences.trim(),
        measures: notice.measures.trim(),
      };
    },
  );
  return { subjects, records, noticeTexts };
}

/** The request body, or what to fix first. */
export function buildIncidentBody(form: IncidentForm, nowMicros: number): BuiltIncident {
  const errors: IncidentFormErrors = { fields: {}, notices: {}, unknownBusinesses: [] };
  const title = form.title.trim().replace(/\s+/g, " ");
  if (!title) {
    errors.fields.title = "required";
  } else if (title.length < TITLE_MIN_LENGTH || title.length > TITLE_MAX_LENGTH) {
    errors.fields.title = "title";
  }
  const { startedAt, detectedAt } = checkTimes(form, nowMicros, errors.fields);
  const isEveryBusiness = form.scope === "all_businesses";
  const businesses = isEveryBusiness ? { ids: [], unknown: [] } : parseBusinessIds(form.businesses);
  if (businesses.unknown.length > 0) {
    errors.fields.businesses = "businessIds";
    errors.unknownBusinesses = businesses.unknown;
  } else if (!isEveryBusiness && businesses.ids.length === 0) {
    errors.fields.businesses = "required";
  } else if (businesses.ids.length > MAX_AFFECTED_BUSINESSES) {
    errors.fields.businesses = "tooManyBusinesses";
  }
  const isBreach = form.kind === "data_breach";
  const breach = isBreach ? checkBreach(form, errors) : null;
  const announcement = form.announce ? buildCreateBody(form.announcement, nowMicros) : null;
  if (announcement && !announcement.ok) {
    errors.announcement = announcement.errors;
  }

  const hasErrors = Object.keys(errors.fields).length > 0 || Object.keys(errors.notices).length > 0 || errors.announcement;
  if (hasErrors || startedAt === null) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    body: {
      kind: form.kind,
      severity: isBreach ? "sev1" : form.severity,
      title,
      started_at: startedAt,
      detected_at: detectedAt,
      scope: form.scope,
      affected_business_ids: businesses.ids,
      approximate_subject_count: breach?.subjects ?? null,
      approximate_record_count: breach?.records ?? null,
      notice_texts: breach?.noticeTexts ?? [],
      announcement: announcement?.ok ? announcement.body : null,
    },
  };
}
