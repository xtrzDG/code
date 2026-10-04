import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";
import { getServerApi, hasSession } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { WhatsNewScreen } from "../_components/WhatsNewScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("changelog.title") };
}

/**
 * /help/whats-new: the cabinet's changelog. For someone signed in the
 * entries they had not read are marked new, and opening the page marks
 * them read.
 */
export default async function WhatsNewPage() {
  const signedIn = await hasSession();
  const progress = signedIn ? await settlePublic((await getServerApi()).GET("/v1/me/help")) : null;
  return <WhatsNewScreen signedIn={progress !== null} readKey={progress?.changelog_read_key ?? null} />;
}
