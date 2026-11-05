import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { LegalDocumentScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/cookies">): Promise<Metadata> {
  return legalPageMetadata(params, "cookies");
}

/** "/it/cookies": the cookie statement in force (GET /v1/legal/cookies), a draft banner while it is one. */
export default async function CookiesPage({ params }: PageProps<"/[locale]/cookies">) {
  const { locale } = await params;
  return <LegalDocumentScreen locale={locale} kind="cookies" />;
}
