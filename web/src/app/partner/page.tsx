import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { TopBar } from "@/components/shell/TopBar";
import { getI18n } from "@/i18n/server";
import { getCurrentUser } from "@/server/api";

import { PartnerScreen } from "./_components/PartnerScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("partnerPortal.title") };
}

/** /partner: the partner portal, for partners only (everyone else gets a 404). */
export default async function PartnerPage() {
  const me = await getCurrentUser();
  if (!me.is_partner) {
    notFound();
  }
  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <main id="main" className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <PartnerScreen />
      </main>
    </div>
  );
}
