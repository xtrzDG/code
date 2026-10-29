import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";
import { getServerApi } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { StatusScreen } from "./_components/StatusScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("platformStatus.title"), description: t("platformStatus.description") };
}

/**
 * /status: whether chats, channels, calls and the cabinet work now, the
 * last 90 days and the team's announcements, for anyone. Rendered with the
 * status the server could read; the page looks again every minute and says
 * so when the platform cannot be reached at all.
 */
export default async function StatusPage() {
  const [{ locale }, api] = await Promise.all([getI18n(), getServerApi()]);
  const status = await settlePublic(api.GET("/v1/platform/status", { params: { query: { language: locale } } }));
  return <StatusScreen initial={status} />;
}
