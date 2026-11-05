import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { CABINET_LANGUAGES, isLocale } from "@/i18n/config";
import { canOpenAdminPage } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { NicheEditorScreen } from "../_components/NicheEditorScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminNiches.title") };
}

/**
 * One niche template's texts in one language (`?language=`, the admin's
 * own by default): GET /v1/admin/niche-templates/{niche_key}.
 */
export default async function AdminNichePage({ params, searchParams }: PageProps<"/admin/niches/[nicheKey]">) {
  const [{ nicheKey }, { language }, me, { locale }] = await Promise.all([params, searchParams, getCurrentUser(), getI18n()]);
  if (!canOpenAdminPage(me, "niches")) {
    notFound();
  }
  const chosen = typeof language === "string" && isLocale(language) && CABINET_LANGUAGES.includes(language) ? language : locale;
  return <NicheEditorScreen nicheKey={nicheKey} language={chosen} />;
}
