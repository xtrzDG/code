import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { canOpenAdminPage } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { PartnersScreen } from "./_components/PartnersScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminPartners.title") };
}

/** The partners, their codes and commissions, and the monthly payouts (/v1/admin/partners). */
export default async function AdminPartnersPage() {
  const me = await getCurrentUser();
  if (!canOpenAdminPage(me, "partners")) {
    notFound();
  }
  return <PartnersScreen me={me} />;
}
