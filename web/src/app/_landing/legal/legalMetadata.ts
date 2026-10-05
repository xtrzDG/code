import "server-only";

import type { Metadata } from "next";

import { isLocale } from "@/i18n/config";
import { getI18n } from "@/i18n/server";
import type { LegalPage } from "@/lib/publicSite/paths";

import { publicPageMetadata } from "../publicMetadata";
import { loadLegalOverview } from "./legalData";

/**
 * Metadata of a public legal or contact page. While the texts are drafts
 * (LEGAL_TEXTS_FINAL off) search engines are asked not to index them: a
 * draft is published to be read, not to be found as the terms in force.
 */
export async function legalPageMetadata(params: Promise<{ locale: string }>, page: LegalPage): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) {
    return {};
  }
  const [{ t }, overview] = await Promise.all([getI18n(), loadLegalOverview()]);
  const metadata = await publicPageMetadata({
    locale,
    rest: `/${page}`,
    title: `${t(`legalPages.nav.${page}`)} · ${t("common.appName")}`,
    description: t(`legalPages.descriptions.${page}`),
    siteName: t("common.appName"),
  });
  const isDraft = overview?.is_draft ?? true;
  return { ...metadata, robots: { index: !isDraft, follow: true } };
}
