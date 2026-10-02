import { LoadingRegion, SkeletonCard, SkeletonPageHeader, SkeletonRows } from "@/components/ui";
import { getI18n } from "@/i18n/server";

/** Any section of a business on its way (its own loading.tsx, if any, takes over once its layout is there). */
export default async function BusinessSectionLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <SkeletonPageHeader />
      <div className="space-y-5">
        <SkeletonCard lines={2} header={false} />
        <SkeletonRows rows={5} />
      </div>
    </LoadingRegion>
  );
}
