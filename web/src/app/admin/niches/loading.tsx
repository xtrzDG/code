import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { NichesSkeleton } from "./_components/NichesScreen";

export default async function AdminNichesLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminNiches.title")} description={t("adminNiches.description")} />
      <NichesSkeleton />
    </>
  );
}
