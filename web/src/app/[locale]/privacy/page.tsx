import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { LegalDocumentScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/privacy">): Promise<Metadata> {
  return legalPageMetadata(params, "privacy");
}

/** "/ru/privacy": the public text in force (GET /v1/legal/privacy), a draft banner while it is one. */
export default async function PrivacyPage({ params }: PageProps<"/[locale]/privacy">) {
  const { locale } = await params;
  return <LegalDocumentScreen locale={locale} kind="privacy" />;
}
