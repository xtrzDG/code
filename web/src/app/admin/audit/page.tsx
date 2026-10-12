import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { canOpenAdminPage } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { AuditScreen } from "../_components/audit/AuditScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminAudit.title") };
}

/** The tamper check of every audit log and the platform's own log (/v1/admin/audit-log). */
export default async function AdminAuditPage() {
  const me = await getCurrentUser();
  if (!canOpenAdminPage(me, "audit")) {
    notFound();
  }
  return <AuditScreen />;
}
