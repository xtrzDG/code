import { LoadingRegion, SkeletonPageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { AdminClientSkeleton } from "../../_components/AdminSkeletons";

export default async function AdminClientLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <SkeletonPageHeader actions />
      <AdminClientSkeleton />
    </LoadingRegion>
  );
}
