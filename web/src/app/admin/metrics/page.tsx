import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { MetricsScreen } from "../_components/metrics/MetricsScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminMetrics.title") };
}

/** The founder's growth metrics (GET /v1/admin/metrics): funnel, MRR, cohorts, Web Vitals. */
export default function AdminMetricsPage() {
  return <MetricsScreen />;
}
