import type { Metadata } from "next";

import { IconShield } from "@/components/icons";
import { Card, EmptyState, PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("pages.admin.title") };
}

/** Placeholder: all clients, health, usage and margin (GET /v1/admin/clients). */
export default async function AdminPage() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("pages.admin.title")} description={t("pages.admin.description")} />
      <Card>
        <EmptyState icon={<IconShield className="size-6" />} title={t("pages.admin.title")} description={t("common.comingSoon")} />
      </Card>
    </>
  );
}
