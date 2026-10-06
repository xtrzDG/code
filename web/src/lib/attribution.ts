/**
 * Where a visitor first came from, for the founder's growth reports: the
 * proxy keeps it in the first-party `aw_attr` cookie on the first visit to
 * the landing page or a hosted chat page (first touch: a later visit never
 * replaces it), and the BFF sends it with the sign-in that creates the
 * account (`signup_attribution` of POST /v1/auth/otp/verify).
 *
 * It holds the link's campaign (utm_*), its `ref` code and `src` tag, the
 * referring site (host only, never its path or query), the first page
 * (path only) and when; nothing that names a person. Every value is checked
 * against the API's rules here, so a strange link can never break a
 * sign-in: a value that does not fit is left out.
 */

import { LOCALES } from "@/i18n/config";

export const ATTRIBUTION_COOKIE = "aw_attr";
/** The first touch counts for 90 days. */
export const ATTRIBUTION_MAX_AGE_SECONDS = 90 * 24 * 60 * 60;

export interface SignupAttribution {
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  referral_code?: string;
  source_tag?: string;
  referrer_host?: string;
  landing_path?: string;
  /** UNIX microseconds, as the API counts time. */
  first_seen_at?: number;
}

type TextField = Exclude<keyof SignupAttribution, "first_seen_at">;

// The rules of the API's primitives (app/schemas/typings/analytics).
const CAMPAIGN_TEXT = /^[^\u0000-\u001f\u007f<>]+$/;
const TAG = /^[A-Za-z0-9._-]+$/;
const HOST = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$/;
const LANDING_PATH = /^\/[A-Za-z0-9_\-/.~%]*$/;

const RULES: Record<TextField, { pattern: RegExp; maxLength: number }> = {
  utm_source: { pattern: CAMPAIGN_TEXT, maxLength: 120 },
  utm_medium: { pattern: CAMPAIGN_TEXT, maxLength: 120 },
  utm_campaign: { pattern: CAMPAIGN_TEXT, maxLength: 120 },
  utm_term: { pattern: CAMPAIGN_TEXT, maxLength: 120 },
  utm_content: { pattern: CAMPAIGN_TEXT, maxLength: 120 },
  referral_code: { pattern: TAG, maxLength: 64 },
  source_tag: { pattern: TAG, maxLength: 64 },
  referrer_host: { pattern: HOST, maxLength: 253 },
  landing_path: { pattern: LANDING_PATH, maxLength: 200 },
};

/** Query parameters of a link and the field each one fills. */
const LINK_PARAMETERS: ReadonlyArray<[string, TextField]> = [
  ["utm_source", "utm_source"],
  ["utm_medium", "utm_medium"],
  ["utm_campaign", "utm_campaign"],
  ["utm_term", "utm_term"],
  ["utm_content", "utm_content"],
  ["ref", "referral_code"],
  ["src", "source_tag"],
];

const HOSTED_CHAT_PREFIX = "/c/";
/** The public site in each language ("/ru", "/ka/restaurants"): "/" redirects there with its query. */
const PUBLIC_SITE_PAGE = new RegExp(`^/(${LOCALES.join("|")})(/|$)`);

/** The landing page, the public site and the hosted chat pages are where visitors arrive. */
export function isAttributionPage(pathname: string): boolean {
  return pathname === "/" || pathname.startsWith(HOSTED_CHAT_PREFIX) || PUBLIC_SITE_PAGE.test(pathname);
}

function cleanText(field: TextField, value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const text = value.trim();
  const rule = RULES[field];
  return text !== "" && text.length <= rule.maxLength && rule.pattern.test(text) ? text : undefined;
}

/** The fields that fit the API's rules; null when none does. */
export function sanitizeAttribution(value: unknown): SignupAttribution | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    return null;
  }
  const source = value as Record<string, unknown>;
  const clean: SignupAttribution = {};
  for (const field of Object.keys(RULES) as TextField[]) {
    const text = cleanText(field, source[field]);
    if (text !== undefined) {
      clean[field] = text;
    }
  }
  const seen = source.first_seen_at;
  if (typeof seen === "number" && Number.isSafeInteger(seen) && seen > 0) {
    clean.first_seen_at = seen;
  }
  return Object.keys(clean).length > 0 ? clean : null;
}

/** The referring site's host, unless it is this site or not a web page. */
function referrerHost(referrer: string | null, ownHost: string): string | undefined {
  if (!referrer) {
    return undefined;
  }
  try {
    const url = new URL(referrer);
    if (url.protocol !== "https:" && url.protocol !== "http:") {
      return undefined;
    }
    const host = url.hostname.toLowerCase().replace(/\.$/, "");
    return host === ownHost.toLowerCase() ? undefined : host;
  } catch {
    return undefined;
  }
}

/** What a first visit to `url` tells, `referrer` being the Referer header. */
export function attributionOfVisit(url: URL, referrer: string | null, nowMs: number): SignupAttribution {
  const raw: Record<string, unknown> = {
    referrer_host: referrerHost(referrer, url.hostname),
    landing_path: url.pathname,
    first_seen_at: Math.floor(nowMs) * 1000,
  };
  for (const [parameter, field] of LINK_PARAMETERS) {
    raw[field] = url.searchParams.get(parameter) ?? undefined;
  }
  return sanitizeAttribution(raw) ?? {};
}

function toBase64Url(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function fromBase64Url(text: string): string {
  const padded = text.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (text.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
  return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
}

/** The cookie's value: JSON in base64url, so no cookie encoding touches it. */
export function encodeAttribution(attribution: SignupAttribution): string {
  return toBase64Url(JSON.stringify(attribution));
}

/** The cookie read back and checked again; null for anything else. */
export function decodeAttribution(value: string | undefined): SignupAttribution | null {
  if (!value || value.length > 4096 || !/^[A-Za-z0-9_-]+$/.test(value)) {
    return null;
  }
  try {
    return sanitizeAttribution(JSON.parse(fromBase64Url(value)));
  } catch {
    return null;
  }
}
