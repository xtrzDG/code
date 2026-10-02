import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { WizardSkeleton } from "./_components/WizardSkeleton";

export default async function ProfileLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <WizardSkeleton />
    </LoadingRegion>
  );
}
