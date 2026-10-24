import type { Metadata } from "next";

import { TopBar } from "@/components/shell/TopBar";
import { getI18n } from "@/i18n/server";
import { safeNextPath } from "@/lib/navigation";

import { LoginScreen } from "./LoginScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("auth.title") };
}

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const query = await searchParams;
  const next = typeof query.next === "string" ? safeNextPath(query.next) : safeNextPath(null);
  const expired = query.reason === "expired";

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar />
      <main id="main" className="flex flex-1 items-start justify-center px-4 py-10 sm:items-center sm:py-16">
        <LoginScreen next={next} sessionExpired={expired} />
      </main>
    </div>
  );
}
