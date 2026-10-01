import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { AdminClientsScreen } from "./_components/AdminClientsScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("pages.admin.title") };
}

/** All clients with health, usage, cost and margin (GET /v1/admin/clients). */
export default function AdminPage() {
  return <AdminClientsScreen />;
}
