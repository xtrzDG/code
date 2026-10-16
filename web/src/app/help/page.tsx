import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";
import { getServerApi, hasSession } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { HelpCenterScreen } from "./_components/HelpCenterScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("helpCenter.title"), description: t("helpCenter.description") };
}

/** /help: the articles by topic, the search, and how to reach support. */
export default async function HelpPage() {
  const [{ locale }, api, signedIn] = await Promise.all([getI18n(), getServerApi(), hasSession()]);
  const center = await settlePublic(api.GET("/v1/help/{language}", { params: { path: { language: locale } } }));
  return <HelpCenterScreen initial={center} signedIn={signedIn} />;
}
