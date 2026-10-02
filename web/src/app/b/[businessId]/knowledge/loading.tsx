import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { KnowledgePageSkeleton } from "./_components/KnowledgeSkeleton";

/** A Knowledge tab on its way (the heading and the tabs stay: they live in the layout). */
export default async function KnowledgeLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <KnowledgePageSkeleton />
    </LoadingRegion>
  );
}
