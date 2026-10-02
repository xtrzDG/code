import { LoadingRegion, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { AdminClientsSkeleton } from "./_components/AdminSkeletons";

export default async function AdminLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("pages.admin.title")} description={t("pages.admin.description")} />
      <LoadingRegion label={t("common.loading")}>
        <AdminClientsSkeleton />
      </LoadingRegion>
    </>
  );
}
