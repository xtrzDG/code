"use client";

import { openCookieSettings } from "./consentEvents";

/** The footer's way back to the cookie choice: reopens the banner. */
export function CookieSettingsButton({ label, className }: { label: string; className?: string }) {
  return (
    <button type="button" className={className} onClick={openCookieSettings} data-testid="cookie-settings">
      {label}
    </button>
  );
}
