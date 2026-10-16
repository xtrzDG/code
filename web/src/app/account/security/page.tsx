import type { Metadata } from "next";

import { TopBar } from "@/components/shell/TopBar";
import { getI18n } from "@/i18n/server";
import { isSecurityReason, safeNextPath } from "@/lib/navigation";
import { getCurrentUser, getServerApi, serverFetch } from "@/server/api";

import { SecurityScreen } from "./_components/SecurityScreen";

export async function generateMetadata(): Promise<Metadata> {
  const { t } = await getI18n();
  return { title: t("security.title") };
}

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

/**
 * Account → Security: the authenticator app, recovery codes and how this
 * session is signed in. A business that requires two factors, or the admin
 * pages, send people here (`?reason=business|admin&next=…`).
 */
export default async function AccountSecurityPage({
  searchParams,
}: PageProps<"/account/security">) {
  const params = await searchParams;
  const api = await getServerApi();
  const [me, security] = await Promise.all([
    getCurrentUser(),
    serverFetch(api.GET("/v1/me/security")),
  ]);
  const reason = first(params.reason);
  const next = first(params.next);

  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <main
        id="main"
        className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 lg:py-12"
      >
        <SecurityScreen
          me={me}
          initial={security}
          reason={isSecurityReason(reason) ? reason : null}
          next={next ? safeNextPath(next, "") || null : null}
        />
      </main>
    </div>
  );
}
