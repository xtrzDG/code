import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { EncryptionKeysScreen } from "../_components/security/EncryptionKeysScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("adminSecurity.title") };
}

/** The key ring and re-encryption of the stored tokens (/v1/admin/security/encryption-keys). */
export default function AdminSecurityPage() {
  return <EncryptionKeysScreen />;
}
