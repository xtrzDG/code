import { PageHeader } from "@/components/ui";
import { getI18n } from "@/i18n/server";

import { EncryptionKeysSkeleton } from "../_components/security/EncryptionKeysScreen";

export default async function AdminSecurityLoading() {
  const { t } = await getI18n();
  return (
    <>
      <PageHeader title={t("adminSecurity.title")} description={t("adminSecurity.description")} />
      <EncryptionKeysSkeleton />
    </>
  );
}
