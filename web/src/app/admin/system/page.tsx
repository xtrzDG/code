import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { SystemScreen } from "../_components/system/SystemScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminSystem.title") };
}

/** The platform's health and the incident log (/v1/admin/system, /v1/admin/incidents). */
export default function AdminSystemPage() {
  return <SystemScreen />;
}
