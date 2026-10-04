import {
  LoadingRegion,
  SkeletonCard,
  SkeletonPageHeader,
} from "@/components/ui";
import { getI18n } from "@/i18n/server";

/** Account → Security while it loads: the header and its three cards. */
export default async function AccountSecurityLoading() {
  const { t } = await getI18n();
  return (
    <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <LoadingRegion label={t("common.loading")}>
        <SkeletonPageHeader />
        <div className="space-y-6">
          <SkeletonCard lines={3} />
          <SkeletonCard lines={2} />
          <SkeletonCard lines={1} />
        </div>
      </LoadingRegion>
    </main>
  );
}
