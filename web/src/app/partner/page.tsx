import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { PartnerScreen } from "./_components/PartnerScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("partnerPortal.title") };
}

/** /partner: the partner portal (the layout lets partners only in). */
export default function PartnerPage() {
  return (
    <main id="main" className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <PartnerScreen />
    </main>
  );
}
