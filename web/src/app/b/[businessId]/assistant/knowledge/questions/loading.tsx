import { LoadingRegion, SkeletonCard, SkeletonRows } from "@/components/ui";
import { getI18n } from "@/i18n/server";

export default async function KnowledgeQuestionsLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")} className="space-y-6">
      <SkeletonCard lines={1} header={false} />
      <SkeletonRows rows={5} />
    </LoadingRegion>
  );
}
