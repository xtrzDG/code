import type { Metadata } from "next";

import { legalPageMetadata } from "../../_landing/legal/legalMetadata";
import { DpaScreen } from "../../_landing/legal/LegalScreens";

export async function generateMetadata({ params }: PageProps<"/[locale]/dpa">): Promise<Metadata> {
  return legalPageMetadata(params, "dpa");
}

/** "/ru/dpa": the data processing agreement in force (GET /v1/legal/overview, then /v1/legal/dpa/{version}). */
export default async function DpaPage({ params }: PageProps<"/[locale]/dpa">) {
  const { locale } = await params;
  return <DpaScreen locale={locale} />;
}
