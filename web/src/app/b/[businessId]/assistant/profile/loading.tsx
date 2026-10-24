import { LoadingRegion } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { ProfileCardsSkeleton } from "./_components/ProfileSkeleton";

export default async function ProfileLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <ProfileCardsSkeleton />
    </LoadingRegion>
  );
}
