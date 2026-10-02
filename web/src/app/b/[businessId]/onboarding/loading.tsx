import { LoadingRegion, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { WizardSkeleton } from "../assistant/profile/_components/WizardSkeleton";

export default async function SetupLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("onboarding.title")} description={t("onboarding.subtitle")} />
      <LoadingRegion label={t("common.loading")}>
        <WizardSkeleton />
      </LoadingRegion>
    </>
  );
}
