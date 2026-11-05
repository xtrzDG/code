import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { TestChatSkeleton } from "./_components/AssistantSkeletons";

/** An Assistant tab on its way (the heading and the tabs stay: they live in the layout). */
export default async function AssistantLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <TestChatSkeleton />
    </LoadingRegion>
  );
}
