/**
 * Channels → Share: where a link will be put (its ?src= tag), how links
 * are named and shown, and the hosted chat page's address rules (the same
 * as the API's BusinessPublicSlug).
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

export type ShareLinks = Schema<"ShareLinksView">;
export type ShareLink = Schema<"ShareLinkView">;
export type ShareLinkKind = ShareLink["kind"];

/** Tags for the places a link goes; "" is no tag. */
export const SHARE_SOURCES = ["", "table", "window", "flyer", "instagram", "google", "website", "email"] as const;

export type ShareSource = (typeof SHARE_SOURCES)[number];

export const SOURCE_LABELS: Record<ShareSource, MessageKey> = {
  "": "share.sources.none",
  table: "share.sources.table",
  window: "share.sources.window",
  flyer: "share.sources.flyer",
  instagram: "share.sources.instagram",
  google: "share.sources.google",
  website: "share.sources.website",
  email: "share.sources.email",
};

export const LINK_KIND_LABELS: Record<ShareLinkKind, MessageKey> = {
  hosted_chat: "share.kinds.hosted_chat",
  whatsapp: "share.kinds.whatsapp",
  telegram: "share.kinds.telegram",
  messenger: "share.kinds.messenger",
  instagram: "share.kinds.instagram",
  phone: "share.kinds.phone",
};

export function isShareSource(value: string): value is ShareSource {
  return (SHARE_SOURCES as readonly string[]).includes(value);
}

/** A link as people read it: without "https://" (a phone link keeps its number). */
export function displayUrl(url: string): string {
  if (url.startsWith("tel:")) {
    return url.slice("tel:".length);
  }
  return url.replace(/^https?:\/\//, "");
}

/** Links that work, first the chat page: what a QR code can be made for. */
export function usableLinks(view: ShareLinks | undefined): (ShareLink & { url: string })[] {
  return (view?.links ?? []).filter((link): link is ShareLink & { url: string } => typeof link.url === "string");
}

/** The name of a downloaded file: "chat-cafe-batumi-whatsapp-table". */
export function downloadName(slug: string, kind: ShareLinkKind, source: ShareSource): string {
  return ["chat", slug, kind === "hosted_chat" ? "" : kind, source].filter(Boolean).join("-").replace(/_/g, "-");
}

export const SLUG_MIN_LENGTH = 3;
export const SLUG_MAX_LENGTH = 40;
const SLUG_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** What the owner types, the way an address is written: "Cafe Batumi" -> "cafe-batumi". */
export function normalizeSlugInput(value: string): string {
  return value
    .toLowerCase()
    .replace(/[\s_]+/g, "-")
    .replace(/[^a-z0-9-]/g, "")
    .slice(0, SLUG_MAX_LENGTH);
}

export function isValidSlug(value: string): boolean {
  return value.length >= SLUG_MIN_LENGTH && value.length <= SLUG_MAX_LENGTH && SLUG_PATTERN.test(value);
}
