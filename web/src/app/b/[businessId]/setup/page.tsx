import type { Metadata } from "next";

import { SetupTunnel } from "@/components/setup/flow/SetupTunnel";
import { getI18n } from "@/i18n/server";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("tunnel.pageTitle") };
}

/**
 * "Create an AI assistant" for a business that exists: the full-screen
 * tunnel from what it offers to the launch (the business frame leaves this
 * page without its sidebar). `?step=hours` opens a step; without it the
 * tunnel opens where the owner left off.
 */
export default function SetupPage() {
  return <SetupTunnel />;
}
