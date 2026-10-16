import "server-only";

import type { Schema } from "@/api/types";
import type { Locale } from "@/i18n/config";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";

export type LegalOverview = Schema<"LegalOverviewView">;
export type LegalText = Schema<"LegalDocumentView">;
export type DpaText = Schema<"DpaDocumentView">;
export type SupportContacts = Schema<"SupportContactsView">;

/** The texts a public legal page renders from GET /v1/legal/{kind} (the DPA has its own route). */
export type LegalTextKind = "terms" | "privacy" | "security";

/** Drafts or final, the DPA in force and the operator (null: the API could not answer). */
export async function loadLegalOverview(): Promise<LegalOverview | null> {
  const api = await getServerApi();
  return settlePublic(api.GET("/v1/legal/overview"));
}

/** The version in force of one text, in the page's language (else its base language, else English). */
export async function loadLegalText(kind: LegalTextKind, locale: Locale): Promise<LegalText | null> {
  const api = await getServerApi();
  return settlePublic(api.GET("/v1/legal/{document}", { params: { path: { document: kind }, query: { language: locale } } }));
}

/** The data processing agreement of one version, in the page's language. */
export async function loadDpaText(version: string, locale: Locale): Promise<DpaText | null> {
  const api = await getServerApi();
  return settlePublic(api.GET("/v1/legal/dpa/{version}", { params: { path: { version }, query: { language: locale } } }));
}

/** How to reach the platform's support (SUPPORT_WHATSAPP, SUPPORT_TELEGRAM, SUPPORT_EMAIL). */
export async function loadSupportContacts(): Promise<SupportContacts | null> {
  const api = await getServerApi();
  return settlePublic(api.GET("/v1/support/contacts"));
}
