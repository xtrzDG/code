import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { MetricsSkeleton } from "../_components/metrics/MetricsScreen";

export default async function AdminMetricsLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminMetrics.title")} description={t("adminMetrics.description")} />
      <MetricsSkeleton />
    </>
  );
}
