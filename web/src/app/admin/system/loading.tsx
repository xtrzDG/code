import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { SystemSkeleton } from "../_components/system/SystemScreen";

export default async function AdminSystemLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminSystem.title")} description={t("adminSystem.description")} />
      <SystemSkeleton />
    </>
  );
}
