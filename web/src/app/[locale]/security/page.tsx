import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { LegalDocumentScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/security">): Promise<Metadata> {
  return legalPageMetadata(params, "security");
}

/** "/ru/security": the public text in force (GET /v1/legal/security), a draft banner while it is one. */
export default async function SecurityPage({ params }: PageProps<"/[locale]/security">) {
  const { locale } = await params;
  return <LegalDocumentScreen locale={locale} kind="security" />;
}
