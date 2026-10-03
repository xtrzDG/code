/**
 * Notification links: `{cabinet}/n/{token}` in every staff e-mail, SMS,
 * chat message and device notification. The token is signed by the API
 * and names a business and a page in it; the page /n/[token] asks the API
 * where it leads (the API checks the signature, the expiry and that the
 * signed-in user works in that business) and opens that page.
 *
 * The token is base64url of: version (1 byte), the business UUID (16
 * bytes), the target code (1), the target UUID (16), the expiry (4) and
 * the signature (12). Only the business is read here, to know which
 * business to ask; nothing read here is trusted.
 */

import type { Schema } from "@/api/types";

import { businessPath } from "./navigation";

export type StaffLinkView = Schema<"StaffLinkView">;

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{40,120}$/;
const TOKEN_LENGTH_BYTES = 1 + 16 + 1 + 16 + 4 + 12;
const BUSINESS_PREFIX = "business_";

function decodeBase64Url(text: string): Uint8Array | null {
  try {
    const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
    const binary = atob(padded);
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
  } catch {
    return null;
  }
}

function uuidOf(bytes: Uint8Array): string {
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** The business a link token names ("business_<uuid>"), or null for something that is not a token. */
export function businessIdOfLinkToken(token: string): string | null {
  if (!TOKEN_PATTERN.test(token)) {
    return null;
  }
  const bytes = decodeBase64Url(token);
  if (bytes === null || bytes.length !== TOKEN_LENGTH_BYTES) {
    return null;
  }
  return `${BUSINESS_PREFIX}${uuidOf(bytes.slice(1, 17))}`;
}

/** The cabinet page a resolved link opens. */
export function linkTargetPath(view: StaffLinkView): string {
  const business = view.business_id;
  switch (view.target) {
    case "conversation":
      return view.conversation_id
        ? `${businessPath(business, "messages")}/${encodeURIComponent(view.conversation_id)}`
        : businessPath(business, "messages/handoffs");
    case "lead":
      return businessPath(business, "messages/leads");
    case "booking": {
      if (!view.booking_date) {
        return businessPath(business, "bookings");
      }
      const query = new URLSearchParams({ range: "custom", from: view.booking_date, to: view.booking_date });
      return `${businessPath(business, "bookings")}?${query.toString()}`;
    }
    case "notifications":
      return businessPath(business, "settings/notifications");
    case "report":
      return view.value_report_id
        ? `${businessPath(business, "overview/reports")}?report=${encodeURIComponent(view.value_report_id)}`
        : businessPath(business, "overview/reports");
  }
}
