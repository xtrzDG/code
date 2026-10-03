import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { TopBar } from "@/components/shell/TopBar";
import { getI18n } from "@/i18n/server";
import { CREATE_PATH } from "@/lib/navigation";
import { getCurrentUser, getServerApi, serverFetch } from "@/server/api";

import { BusinessesScreen } from "./BusinessesScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("businesses.title") };
}

/**
 * The businesses of the signed-in user. A new account has nothing to list
 * yet: it goes straight into "Create an AI assistant".
 */
export default async function BusinessesPage() {
  const api = await getServerApi();
  const [me, businesses] = await Promise.all([getCurrentUser(), serverFetch(api.GET("/v1/businesses"))]);
  if (businesses.length === 0 && (me.memberships ?? []).length === 0) {
    redirect(CREATE_PATH);
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        <BusinessesScreen businesses={businesses} />
      </main>
    </div>
  );
}
