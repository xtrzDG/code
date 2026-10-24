import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { VersionDetailSkeleton } from "../../_components/AssistantSkeletons";

export default async function VersionLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <VersionDetailSkeleton />
    </LoadingRegion>
  );
}
