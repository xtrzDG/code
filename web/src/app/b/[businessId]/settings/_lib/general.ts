/**
 * Pure helpers of the Settings page's General tab: the settings form, its
 * PATCH body and the language choices.
 */

import type { RequestBody, Schema } from "@/api/types";

export type BusinessView = Schema<"BusinessView">;

export type SettingsChanges = RequestBody<"/v1/businesses/{business_id}", "patch">;

export const MAX_BUSINESS_NAME_LENGTH = 200;
export const MAX_CITY_LENGTH = 120;
export const MIN_RETENTION_DAYS = 1;
export const MAX_RETENTION_DAYS = 3650;

export interface GeneralForm {
  name: string;
  city: string;
  timezone: string;
  languages: string[];
  defaultLanguage: string;
  ownerLanguage: string;
  retentionDays: string;
}

export type GeneralField = keyof GeneralForm;
export type GeneralError = "required" | "tooLong" | "languages" | "retention";

export function generalFormFrom(business: BusinessView): GeneralForm {
  return {
    name: business.name,
    city: business.city ?? "",
    timezone: business.timezone,
    languages: [...business.languages],
    defaultLanguage: business.default_language,
    ownerLanguage: business.owner_language,
    retentionDays: String(business.recording_retention_days),
  };
}

/** "90" -> 90; anything that is not a whole number in 1..3650 -> null. */
export function parseRetentionDays(text: string): number | null {
  const trimmed = text.trim();
  if (!/^\d+$/.test(trimmed)) {
    return null;
  }
  const days = Number(trimmed);
  return days >= MIN_RETENTION_DAYS && days <= MAX_RETENTION_DAYS ? days : null;
}

export function sameList(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && left.every((value, index) => value === right[index]);
}

export type GeneralResult =
  | { ok: true; changes: SettingsChanges }
  | { ok: false; errors: Partial<Record<GeneralField, GeneralError>> };

/**
 * The PATCH body with only the fields that changed, or the fields to fix.
 * A default language that dropped out of the list falls back to the first one.
 */
export function buildGeneralChanges(business: BusinessView, form: GeneralForm): GeneralResult {
  const errors: Partial<Record<GeneralField, GeneralError>> = {};
  const name = form.name.trim();
  const city = form.city.trim();
  if (name === "") {
    errors.name = "required";
  } else if (name.length > MAX_BUSINESS_NAME_LENGTH) {
    errors.name = "tooLong";
  }
  if (city.length > MAX_CITY_LENGTH) {
    errors.city = "tooLong";
  }
  if (form.languages.length === 0) {
    errors.languages = "languages";
  }
  const retention = parseRetentionDays(form.retentionDays);
  if (retention === null) {
    errors.retentionDays = "retention";
  }
  if (Object.keys(errors).length > 0 || retention === null) {
    return { ok: false, errors };
  }

  const defaultLanguage = form.languages.includes(form.defaultLanguage) ? form.defaultLanguage : form.languages[0];
  const changes: SettingsChanges = {};
  if (name !== business.name) {
    changes.name = name;
  }
  if (city !== (business.city ?? "")) {
    changes.city = city;
  }
  if (form.timezone !== business.timezone) {
    changes.timezone = form.timezone;
  }
  if (!sameList(form.languages, business.languages)) {
    changes.languages = form.languages;
  }
  if (defaultLanguage && defaultLanguage !== business.default_language) {
    changes.default_language = defaultLanguage;
  }
  if (form.ownerLanguage !== business.owner_language) {
    changes.owner_language = form.ownerLanguage;
  }
  if (retention !== business.recording_retention_days) {
    changes.recording_retention_days = retention;
  }
  return { ok: true, changes };
}

export function hasChanges(changes: SettingsChanges): boolean {
  return Object.keys(changes).length > 0;
}

/** Languages to offer: the business's own first, then the others, without repeats. */
export function languageChoices(...groups: readonly (readonly string[])[]): string[] {
  return [...new Set(groups.flat())];
}

/** Toggle a language and keep the order of `choices`. */
export function toggleLanguage(selected: readonly string[], tag: string, isOn: boolean, choices: readonly string[]): string[] {
  const next = new Set(selected);
  if (isOn) {
    next.add(tag);
  } else {
    next.delete(tag);
  }
  const ordered = choices.filter((choice) => next.has(choice));
  const rest = [...next].filter((choice) => !choices.includes(choice));
  return [...ordered, ...rest];
}
