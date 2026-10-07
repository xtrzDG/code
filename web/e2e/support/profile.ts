/**
 * Assistant → Business profile in the tests: its six sections, the texts
 * the banner over the page shows for a number of changes, and how many
 * changes customers do not get yet (read from the API, so a test can
 * start from whatever an earlier test left).
 */

import { expect, type APIRequestContext, type Page } from "@playwright/test";

import type { Messages } from "../../src/i18n/translate";

import { API_URL } from "./env";

/** The sections in the order of their cards (src/lib/profile/sections.ts). */
export const PROFILE_SECTIONS = ["business", "place", "offer", "hours", "people", "rules"] as const;

export type ProfileSection = (typeof PROFILE_SECTIONS)[number];

/** The cabinet's texts in any of its languages (ru and ka are typed against English). */
export type { Messages };

export function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** A dictionary template as a pattern: "Step {number} of {total}" matches "Step 4 of 8". */
export function templatePattern(template: string): RegExp {
  return new RegExp(template.split(/\{[a-z]+\}/i).map(escapeRegExp).join(".+"));
}

/** A plural text of the dictionary for `count`, as the cabinet renders it. */
export function pluralText(forms: Readonly<Record<string, string>>, locale: string, count: number): string {
  const category = new Intl.PluralRules(locale).select(count);
  return (forms[category] ?? forms.other ?? "").replace("{count}", String(count));
}

/** "Edit Hours and bookings": the name of a section's card. */
export function cardName(messages: Messages, section: ProfileSection): string {
  return messages.profileEdit.open.replace("{section}", messages.profileEdit.sections[section].title);
}

/** How many changes customers of a live business do not get yet (0 while it is not live). */
export async function pendingCount(request: APIRequestContext, token: string, businessId: string): Promise<number> {
  const response = await request.get(`${API_URL}/v1/businesses/${businessId}/assistant/pending-changes?language=en`, {
    headers: { authorization: `Bearer ${token}` },
  });
  expect(response.status(), await response.text()).toBe(200);
  const view = (await response.json()) as { is_live: boolean; count: number };
  return view.is_live ? view.count : 0;
}

/** The editor's save state ("Saving…", "Saved", "Not saved") at its top. */
export function saveState(page: Page) {
  return page.locator("[data-save-state]");
}

/** Monday's closing time in the week of "Hours and bookings" (the first day of the week): a TimeField (support/timeField.ts). */
export function firstClosingTime(page: Page, messages: Messages) {
  return page.getByRole("group", { name: new RegExp(`: ${escapeRegExp(messages.onboarding.week.closes)}$`) }).first();
}
