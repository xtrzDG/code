import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { canOpenAdminPage } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { NichesScreen } from "./_components/NichesScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminNiches.title") };
}

/** Every niche template and the state of its texts (/v1/admin/niche-templates). */
export default async function AdminNichesPage() {
  const me = await getCurrentUser();
  if (!canOpenAdminPage(me, "niches")) {
    notFound();
  }
  return <NichesScreen />;
}
