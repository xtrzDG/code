/**
 * The hosted chat page (/c/{address}) learns its business from the API's
 * public GET /v1/public/chat/{address}. The proxy asks once per page view:
 * it needs the API's address for the page's Content Security Policy
 * (connect-src) and moves older addresses to the current one; it hands
 * what it learned to the page in a request header, so the page does not
 * ask again. Nothing in it is secret: the API returns it to anyone.
 */

import type { Schema } from "@/api/types";

import { buildUpstreamHeaders, callBackend, getBackendUrl, sanitizeRequestId } from "./backend";

export type HostedChatView = Schema<"HostedChatView">;

export type HostedChatLookup =
  | { kind: "found"; view: HostedChatView }
  /** No business has this address. */
  | { kind: "missing" }
  /** The API did not answer in time or failed. */
  | { kind: "failed" };

/** Request header with the encoded lookup, set by the proxy, read by the page. */
export const HOSTED_CHAT_HEADER = "x-aw-hosted-chat";

const HOSTED_CHAT_PREFIX = "/c/";
/** A slug (lower case letters, digits, hyphens) or a business id. */
const ADDRESS_PATTERN = /^[A-Za-z0-9_-]{1,80}$/;
const LOOKUP_TIMEOUT_MS = 4_000;
const ENCODED_VIEW_PREFIX = "v1.";

/**
 * The address of a hosted chat page path, or null for any other path:
 * "/c/cafe-batumi" -> "cafe-batumi"; "/c/cafe-batumi/privacy" -> null.
 */
export function hostedChatAddress(pathname: string): string | null {
  if (!pathname.startsWith(HOSTED_CHAT_PREFIX)) {
    return null;
  }
  const address = pathname.slice(HOSTED_CHAT_PREFIX.length).replace(/\/$/, "");
  return ADDRESS_PATTERN.test(address) ? address : null;
}

export function isHostedChatPath(pathname: string): boolean {
  return pathname === "/c" || pathname.startsWith(HOSTED_CHAT_PREFIX);
}

/** The page of an address, with the query of the original visit: "/c/new-name?src=qr". */
export function hostedChatPath(address: string, search = ""): string {
  return `${HOSTED_CHAT_PREFIX}${encodeURIComponent(address)}${search}`;
}

/** Ask the API about an address; the visitor's languages go along (Accept-Language). */
export async function lookUpHostedChat(address: string, incoming: Headers | null): Promise<HostedChatLookup> {
  try {
    const response = await callBackend(`/v1/public/chat/${encodeURIComponent(address)}`, {
      headers: buildUpstreamHeaders(incoming, { requestId: sanitizeRequestId(incoming?.get("x-request-id")) }),
      timeoutMs: LOOKUP_TIMEOUT_MS,
    });
    if (response.status === 404) {
      return { kind: "missing" };
    }
    if (!response.ok) {
      return { kind: "failed" };
    }
    return { kind: "found", view: (await response.json()) as HostedChatView };
  } catch {
    return { kind: "failed" };
  }
}

/** The lookup as a header value: "missing", "failed" or "v1." + base64url JSON (names are UTF-8). */
export function encodeLookup(lookup: HostedChatLookup): string {
  if (lookup.kind !== "found") {
    return lookup.kind;
  }
  const bytes = new TextEncoder().encode(JSON.stringify(lookup.view));
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return ENCODED_VIEW_PREFIX + btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** The lookup the proxy handed over; "failed" when the header is missing or broken. */
export function decodeLookup(value: string | null): HostedChatLookup {
  if (value === "missing") {
    return { kind: "missing" };
  }
  if (!value || !value.startsWith(ENCODED_VIEW_PREFIX)) {
    return { kind: "failed" };
  }
  try {
    const base64 = value.slice(ENCODED_VIEW_PREFIX.length).replace(/-/g, "+").replace(/_/g, "/");
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    const view = JSON.parse(new TextDecoder().decode(bytes)) as HostedChatView;
    return typeof view.business_id === "string" ? { kind: "found", view } : { kind: "failed" };
  } catch {
    return { kind: "failed" };
  }
}

/**
 * Where the browser reaches the API: the API's public address (APP_BASE_URL),
 * else BACKEND_URL, which works only where the browser can reach it (local
 * runs and the end-to-end suite).
 */
export function chatApiBase(view: HostedChatView, env: Record<string, string | undefined> = process.env): string {
  return (view.api_base_url ?? getBackendUrl(env)).replace(/\/+$/, "");
}

/** The origin of an address, or null when it is not an http(s) URL. */
export function originOf(url: string): string | null {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.origin : null;
  } catch {
    return null;
  }
}
