import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";
import { hasAdminPermission } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { AdminClientScreen } from "../../_components/AdminClientScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: `${t("admin.columns.client")} · ${t("pages.admin.title")}` };
}

/**
 * One client in detail (GET /v1/admin/clients/{business_id}), "open
 * cabinet", and what the admin's role may do there: account actions,
 * writing notes (the API checks the same at every request).
 */
export default async function AdminClientPage({ params }: PageProps<"/admin/clients/[businessId]">) {
  const [{ businessId }, me] = await Promise.all([params, getCurrentUser()]);
  return (
    <AdminClientScreen
      businessId={businessId}
      canManageBilling={hasAdminPermission(me, "manage_client_billing")}
      canWriteNotes={hasAdminPermission(me, "write_client_notes")}
    />
  );
}
