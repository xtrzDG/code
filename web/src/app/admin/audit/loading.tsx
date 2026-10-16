import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { AuditSkeleton } from "../_components/audit/AuditScreen";

export default async function AdminAuditLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminAudit.title")} description={t("adminAudit.description")} />
      <AuditSkeleton />
    </>
  );
}
