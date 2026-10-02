import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { AdminShell } from "@/components/shell/AdminShell";
import { SIDEBAR_COOKIE, readSidebarState } from "@/lib/shellPreferences";
import { getCurrentUser } from "@/server/api";

/** /admin/* is only for platform admins; everyone else gets a 404. */
export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  const [me, cookieStore] = await Promise.all([getCurrentUser(), cookies()]);
  if (!me.user.is_platform_admin) {
    notFound();
  }
  const collapsed = readSidebarState(cookieStore.get(SIDEBAR_COOKIE)?.value) === "collapsed";
  return (
    <AdminShell me={me} initialCollapsed={collapsed}>
      {children}
    </AdminShell>
  );
}
