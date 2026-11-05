/**
 * The footer's "Cookie settings" button and the banner talk through one
 * window event, so the button needs nothing but this name to reopen the
 * banner wherever it is on the page. The event names the button, so focus
 * can return to it after the answer (Safari does not focus a clicked button).
 */

export const OPEN_COOKIE_SETTINGS_EVENT = "aw:open-cookie-settings";

export type OpenCookieSettingsEvent = CustomEvent<{ opener: HTMLElement | null }>;

/** Reopen the cookie banner (the visitor wants to change their choice). */
export function openCookieSettings(opener: HTMLElement | null): void {
  window.dispatchEvent(new CustomEvent(OPEN_COOKIE_SETTINGS_EVENT, { detail: { opener } }));
}
