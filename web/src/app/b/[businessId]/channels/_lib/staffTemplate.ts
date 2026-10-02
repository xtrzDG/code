/** The WhatsApp template staff replies are sent in after the 24-hour window. */

import type { RequestBody } from "@/api/types";

export type StaffTemplateBody = RequestBody<"/v1/businesses/{business_id}/channels/whatsapp/staff-template", "put">;

export type StaffTemplateFieldError = "required" | "name" | "language";

export type StaffTemplateFormResult =
  | { ok: true; body: StaffTemplateBody }
  | { ok: false; errors: { name?: StaffTemplateFieldError; language?: StaffTemplateFieldError } };

/** Names Meta accepts for templates: lowercase Latin letters, digits and "_". */
const TEMPLATE_NAME = /^[a-z0-9_]{1,512}$/;
/** Template languages as WhatsApp writes them: "en", "pt_BR". */
const TEMPLATE_LANGUAGE = /^[a-z]{2,3}(_[A-Z]{2})?$/;

/**
 * The request that saves the template for staff replies: both fields set
 * it (a "pt-BR" typed with a hyphen is read as "pt_BR"); the API removes
 * it with an empty body, which the form sends from its own Remove button.
 */
export function buildStaffTemplateBody(name: string, language: string): StaffTemplateFormResult {
  const templateName = name.trim();
  const [base = "", region] = language.trim().replace("-", "_").split("_");
  const languageCode = region === undefined ? base.toLowerCase() : `${base.toLowerCase()}_${region.toUpperCase()}`;
  const errors: { name?: StaffTemplateFieldError; language?: StaffTemplateFieldError } = {};
  if (!templateName) {
    errors.name = "required";
  } else if (!TEMPLATE_NAME.test(templateName)) {
    errors.name = "name";
  }
  if (!languageCode) {
    errors.language = "required";
  } else if (!TEMPLATE_LANGUAGE.test(languageCode)) {
    errors.language = "language";
  }
  if (errors.name || errors.language) {
    return { ok: false, errors };
  }
  return { ok: true, body: { name: templateName, language_code: languageCode } };
}
