import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { ContactScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/contact">): Promise<Metadata> {
  return legalPageMetadata(params, "contact");
}

/** "/ru/contact": the operator's details and the support channels. */
export default async function ContactPage({ params }: PageProps<"/[locale]/contact">) {
  const { locale } = await params;
  return <ContactScreen locale={locale} />;
}
