import { LoadingRegion, SkeletonCard } from "@/components/ui";
import { getI18n } from "@/i18n/server";

/** A settings page on its way (the heading and the tabs stay: they live in the layout). */
export default async function SettingsLoading() {
  const { t } = await getI18n();
  return (
    <LoadingRegion label={t("common.loading")}>
      <div className="space-y-6">
        <SkeletonCard lines={3} />
        <SkeletonCard lines={5} />
      </div>
    </LoadingRegion>
  );
}
