import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { NicheEditorSkeleton } from "../_components/NicheEditorScreen";

export default async function AdminNicheLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminNiches.title")} />
      <NicheEditorSkeleton />
    </>
  );
}
