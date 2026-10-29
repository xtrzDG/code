import { LoadingRegion, SkeletonText } from "@/components/ui";
import { getI18n } from "@/i18n/server";

export default async function CreateLoading() {
  const { t } = await getI18n();
  return (
    <div className="mx-auto flex min-h-dvh max-w-2xl items-center px-4">
      <LoadingRegion label={t("common.loading")} className="w-full">
        <SkeletonText lines={4} />
      </LoadingRegion>
    </div>
  );
}
