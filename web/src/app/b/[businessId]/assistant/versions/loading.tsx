import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { VersionsSkeleton } from "../_components/AssistantSkeletons";

export default async function VersionsLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <VersionsSkeleton />
    </LoadingRegion>
  );
}
