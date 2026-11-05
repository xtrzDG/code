import type { Metadata } from "next";

import { getI18n } from "@/i18n/server";

import { BrandsScreen } from "./_components/BrandsScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("brands.title") };
}

/** /brands: the brands the person belongs to, and a new one from a business they own. */
export default function BrandsPage() {
  return (
    <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
      <BrandsScreen />
    </main>
  );
}
