import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { AdminClientScreen } from "../../_components/AdminClientScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: `${t("admin.columns.client")} · ${t("pages.admin.title")}` };
}

/** One client in detail (GET /v1/admin/clients/{business_id}) and "open cabinet". */
export default async function AdminClientPage({ params }: PageProps<"/admin/clients/[businessId]">) {
  const { businessId } = await params;
  return <AdminClientScreen businessId={businessId} />;
}
