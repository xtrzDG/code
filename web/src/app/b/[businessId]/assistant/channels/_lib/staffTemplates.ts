/**
 * The WhatsApp templates staff replies go out in after the 24-hour window,
 * one per language: a reply takes the template of the customer's language,
 * else the one of the business's main language. The editor keeps rows of
 * language + template name; the API takes the whole list at once.
 */

import type { RequestBody, Schema } from "@/api/types";

import type { ChannelView } from "./channels";

export type StaffTemplatesBody = RequestBody<"/v1/businesses/{business_id}/channels/whatsapp/staff-templates", "put">;
export type StaffTemplate = Schema<"WhatsAppStaffTemplateView">;

export interface TemplateRow {
  /** A stable key for React while rows come and go. */
  key: string;
  language: string;
  name: string;
}

export type TemplateRowError = "required" | "name" | "language" | "duplicate";

export interface TemplateRowErrors {
  language?: TemplateRowError;
  name?: TemplateRowError;
}

export type StaffTemplatesResult =
  | { ok: true; body: StaffTemplatesBody }
  | { ok: false; errors: Record<string, TemplateRowErrors> };

/** Names Meta accepts for templates: lowercase Latin letters, digits and "_". */
const TEMPLATE_NAME = /^[a-z0-9_]{1,512}$/;
/** Template languages as WhatsApp writes them: "en", "pt_BR". */
const TEMPLATE_LANGUAGE = /^[a-z]{2,3}(_[A-Z]{2})?$/;

/** A language as WhatsApp writes it: "pt-br" -> "pt_BR", "KA" -> "ka". */
export function templateLanguageCode(text: string): string {
  const [base = "", region] = text.trim().replace("-", "_").split("_");
  return region === undefined ? base.toLowerCase() : `${base.toLowerCase()}_${region.toUpperCase()}`;
}

/** The saved templates (a channel saved by an older release has only the single one). */
export function savedStaffTemplates(channel: Pick<ChannelView, "staff_reply_templates" | "staff_reply_template">): StaffTemplate[] {
  const templates = channel.staff_reply_templates ?? [];
  if (templates.length > 0) {
    return templates;
  }
  return channel.staff_reply_template ? [channel.staff_reply_template] : [];
}

/** A key that changes whenever the saved templates do (the editor then starts again from them). */
export function staffTemplatesKey(channel: Pick<ChannelView, "staff_reply_templates" | "staff_reply_template">): string {
  return savedStaffTemplates(channel)
    .map((template) => `${template.language_code}:${template.name}`)
    .join(",");
}

let rowCounter = 0;

export function newTemplateRow(language = "", name = ""): TemplateRow {
  rowCounter += 1;
  return { key: `template-${rowCounter}`, language, name };
}

export function templateRows(templates: readonly StaffTemplate[]): TemplateRow[] {
  return templates.map((template) => newTemplateRow(template.language_code, template.name));
}

/**
 * The language to offer on a new row: the first business language without
 * a template yet (main language first), else nothing.
 */
export function nextTemplateLanguage(
  businessLanguages: readonly string[],
  defaultLanguage: string,
  rows: readonly TemplateRow[],
): string {
  const used = new Set(rows.map((row) => templateLanguageCode(row.language).split("_")[0]));
  const candidates = [defaultLanguage, ...businessLanguages];
  return candidates.map(templateLanguageCode).find((code) => !used.has(code.split("_")[0])) ?? "";
}

/**
 * The request body for the rows, or what to fix per row. Fully empty rows
 * are dropped; each language may have one template.
 */
export function buildStaffTemplatesBody(rows: readonly TemplateRow[]): StaffTemplatesResult {
  const errors: Record<string, TemplateRowErrors> = {};
  const templates: StaffTemplate[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    const name = row.name.trim();
    const language = templateLanguageCode(row.language);
    if (!name && !language) {
      continue;
    }
    const rowErrors: TemplateRowErrors = {};
    if (!language) {
      rowErrors.language = "required";
    } else if (!TEMPLATE_LANGUAGE.test(language)) {
      rowErrors.language = "language";
    } else if (seen.has(language)) {
      rowErrors.language = "duplicate";
    }
    if (!name) {
      rowErrors.name = "required";
    } else if (!TEMPLATE_NAME.test(name)) {
      rowErrors.name = "name";
    }
    if (rowErrors.language || rowErrors.name) {
      errors[row.key] = rowErrors;
      continue;
    }
    seen.add(language);
    templates.push({ language_code: language, name });
  }
  return Object.keys(errors).length > 0 ? { ok: false, errors } : { ok: true, body: { templates } };
}

/** Whether the rows say the same as the saved templates (in any order). */
export function isSameTemplates(rows: readonly TemplateRow[], saved: readonly StaffTemplate[]): boolean {
  const built = buildStaffTemplatesBody(rows);
  if (!built.ok) {
    return false;
  }
  const key = (template: StaffTemplate) => `${template.language_code}:${template.name}`;
  const left = (built.body.templates ?? []).map(key).sort();
  const right = saved.map(key).sort();
  return left.length === right.length && left.every((value, index) => value === right[index]);
}
