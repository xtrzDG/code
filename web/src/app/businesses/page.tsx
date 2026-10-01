import type { Metadata } from "next";

import { TopBar } from "@/components/shell/TopBar";
import { getI18n } from "@/i18n/server";
import { getCurrentUser, getServerApi, serverFetch } from "@/server/api";

import { BusinessesScreen } from "./BusinessesScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("businesses.title") };
}

export default async function BusinessesPage() {
  const api = await getServerApi();
  const [me, businesses] = await Promise.all([getCurrentUser(), serverFetch(api.GET("/v1/businesses"))]);

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <BusinessesScreen me={me} businesses={businesses} />
      </main>
    </div>
  );
}
