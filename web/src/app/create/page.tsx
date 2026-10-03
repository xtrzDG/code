import type { Metadata } from "next";

import { CreateTunnel } from "@/components/setup/create/CreateTunnel";
import { getI18n } from "@/i18n/server";
import { getCurrentUser } from "@/server/api";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("tunnel.pageTitle") };
}

/**
 * "Create an AI assistant": the full-screen tunnel for a new business (the
 * landing's button, "New assistant" in the business switcher, an account
 * without businesses). Visitors without a session sign in first and come
 * back here (src/proxy.ts).
 */
export default async function CreatePage() {
  const me = await getCurrentUser();
  return <CreateTunnel me={me} />;
}
