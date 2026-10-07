import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { SectionEditorSkeleton } from "../_components/ProfileSkeleton";

export default async function ProfileSectionLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <SectionEditorSkeleton />
    </LoadingRegion>
  );
}
