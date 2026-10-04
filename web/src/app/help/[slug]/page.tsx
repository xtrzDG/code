import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { getI18n } from "@/i18n/server";
import { isHelpArticleSlug } from "@/lib/help/helpTopics";
import { getServerApi, hasSession } from "@/server/api";
import { settlePublic } from "@/server/publicData";

import { HelpArticleScreen } from "../_components/HelpArticleScreen";

async function loadArticle(slug: string) {
  const [{ locale }, api] = await Promise.all([getI18n(), getServerApi()]);
  return settlePublic(api.GET("/v1/help/{language}/{slug}", { params: { path: { language: locale, slug } } }));
}

export async function generateMetadata({ params }: PageProps<"/help/[slug]">): Promise<Metadata> {
  const { t } = await getI18n();
  const article = await loadArticle((await params).slug);
  return article ? { title: article.title, description: article.summary } : { title: t("helpCenter.title") };
}

/** /help/{slug}: one article of the help center; an unknown address is "Page not found". */
export default async function HelpArticlePage({ params }: PageProps<"/help/[slug]">) {
  const { slug } = await params;
  if (!isHelpArticleSlug(slug)) {
    notFound();
  }
  const [article, signedIn] = await Promise.all([loadArticle(slug), hasSession()]);
  return <HelpArticleScreen slug={slug} initial={article} signedIn={signedIn} />;
}
