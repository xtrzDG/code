import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { LegalDocumentScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/terms">): Promise<Metadata> {
  return legalPageMetadata(params, "terms");
}

/** "/ru/terms": the public text in force (GET /v1/legal/terms), a draft banner while it is one. */
export default async function TermsPage({ params }: PageProps<"/[locale]/terms">) {
  const { locale } = await params;
  return <LegalDocumentScreen locale={locale} kind="terms" />;
}
