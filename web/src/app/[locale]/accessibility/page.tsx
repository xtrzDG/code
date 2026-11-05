import type { Metadata } from "next";

import { AccessibilityScreen } from "../../_landing/legal/AccessibilityScreen";
import { legalPageMetadata } from "../../_landing/legal/legalMetadata";

export async function generateMetadata({ params }: PageProps<"/[locale]/accessibility">): Promise<Metadata> {
  return legalPageMetadata(params, "accessibility");
}

/** "/it/accessibility": the accessibility statement (AgID's model), in the page's language. */
export default async function AccessibilityPage({ params }: PageProps<"/[locale]/accessibility">) {
  const { locale } = await params;
  return <AccessibilityScreen locale={locale} />;
}
