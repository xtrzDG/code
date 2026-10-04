/**
 * The links the assistant may send (menu, map, payment page, booking page,
 * delivery, website, privacy notice, Google reviews) as rows of the
 * profile editor: one row per kind, checked as typed and saved without
 * the empty ones.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { webLinkSchema } from "../validation";

export type LinkKind = Schema<"BusinessLinkKind">;

/** Every kind, in the order the editor offers them. */
export const LINK_KINDS: readonly LinkKind[] = ["website", "menu", "map", "booking_page", "payment", "delivery", "google_review", "privacy"];

export interface LinkRow {
  key: string;
  kind: LinkKind;
  url: string;
}

export function linkRowsFrom(links: readonly Schema<"BusinessLink">[] | null | undefined): LinkRow[] {
  return (links ?? []).map((link) => ({ key: `link-${link.kind}`, kind: link.kind, url: link.url }));
}

/** Kinds not on a row yet (each kind once). */
export function freeLinkKinds(rows: readonly Pick<LinkRow, "kind">[]): LinkKind[] {
  const used = new Set(rows.map((row) => row.kind));
  return LINK_KINDS.filter((kind) => !used.has(kind));
}

/** Rows whose address the API would refuse, by row key. */
export function linkProblems(rows: readonly LinkRow[]): Record<string, MessageKey> {
  const problems: Record<string, MessageKey> = {};
  for (const row of rows) {
    if (row.url.trim() !== "" && !webLinkSchema.safeParse(row.url).success) {
      problems[row.key] = "validation.url";
    }
  }
  return problems;
}

/** The profile's `links`: the rows with an address, trimmed. */
export function linksPayload(rows: readonly LinkRow[]): Schema<"BusinessLink">[] {
  return rows.filter((row) => row.url.trim() !== "").map((row) => ({ kind: row.kind, url: row.url.trim() }));
}
