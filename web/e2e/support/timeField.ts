/**
 * The UI kit's TimeField (components/ui/TimeField.tsx): not one input but a
 * group of spinbuttons, hours and minutes, and AM/PM where the cabinet's
 * language has a 12-hour clock (English). Its value is on the group's
 * `data-value`, "HH:MM" on a 24-hour clock.
 */

import { expect, type Locator, type Page } from "@playwright/test";

/** A TimeField by its label (the Field's label, or its own aria-label). */
export function timeField(scope: Page | Locator, label: string | RegExp): Locator {
  return scope.getByRole("group", { name: label });
}

/**
 * Types a 24-hour "HH:MM" the way a person does: the hours, the minutes,
 * and "a" or "p" where the clock has AM/PM.
 */
export async function typeTime(field: Locator, time: string): Promise<void> {
  const [hours = "", minutes = ""] = time.split(":");
  const hour = Number(hours);
  const segments = field.getByRole("spinbutton");
  await segments.first().click();
  const keyboard = field.page().keyboard;
  if ((await segments.count()) === 3) {
    await keyboard.type(`${String(hour % 12 || 12).padStart(2, "0")}${minutes}`);
    await keyboard.type(hour < 12 ? "a" : "p");
  } else {
    await keyboard.type(`${hours}${minutes}`);
  }
}

/** The time the field holds, "HH:MM" on a 24-hour clock ("" when empty). */
export async function timeValue(field: Locator): Promise<string> {
  return (await field.getAttribute("data-value")) ?? "";
}

export async function expectTime(field: Locator, time: string): Promise<void> {
  await expect(field).toHaveAttribute("data-value", time);
}

/** What the field shows: "08 : 00" reads "08:00" (the AM/PM segment, when there is one, after a space). */
export async function shownTime(field: Locator): Promise<string> {
  const parts = await field.getByRole("spinbutton").evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value));
  const [hours = "", minutes = "", period] = parts;
  return period === undefined ? `${hours}:${minutes}` : `${hours}:${minutes} ${period}`;
}
