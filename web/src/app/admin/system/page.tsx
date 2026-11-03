import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";
import { hasAdminPermission } from "@/lib/adminPermissions";
import { getCurrentUser } from "@/server/api";

import { SystemScreen } from "../_components/system/SystemScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminSystem.title") };
}

/**
 * The platform's health and the incident log (/v1/admin/system,
 * /v1/admin/incidents); SUPER admins (manage_operations) also get the
 * global pause of every assistant (/v1/admin/platform/pause).
 */
export default async function AdminSystemPage() {
  const me = await getCurrentUser();
  return (
    <SystemScreen canPause={hasAdminPermission(me, "manage_operations")} userId={me.user.id} />
  );
}
