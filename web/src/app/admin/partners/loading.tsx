import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { PartnersSkeleton } from "./_components/PartnersScreen";

export default async function AdminPartnersLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminPartners.title")} description={t("adminPartners.description")} />
      <PartnersSkeleton />
    </>
  );
}
