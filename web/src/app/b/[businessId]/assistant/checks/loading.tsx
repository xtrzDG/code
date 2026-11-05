import { LoadingRegion, SkeletonCardList } from "@/components/ui";
import { getI18n } from "@/i18n/server";

export default async function ChecksLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("teaching.checks.loading")}>
      <SkeletonCardList cards={3} />
    </LoadingRegion>
  );
}
