import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import { AdminShell } from "@/components/shell/AdminShell";
import { ADMIN_PATH, securityPath } from "@/lib/navigation";
import { SIDEBAR_COOKIE, readSidebarState } from "@/lib/shellPreferences";
import { getCurrentUser } from "@/server/api";

/**
 * /admin/* is only for platform admins (everyone else gets a 404), and only
 * with a session signed in with two factors (else Account → Security).
 */
export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  const [me, cookieStore] = await Promise.all([getCurrentUser(), cookies()]);
  if (!me.user.is_platform_admin) {
    notFound();
  }
  if (me.auth_level !== "two_factor") {
    // The admin pages take only sessions signed in with the authenticator app.
    redirect(securityPath({ reason: "admin", next: ADMIN_PATH }));
  }
  const collapsed = readSidebarState(cookieStore.get(SIDEBAR_COOKIE)?.value) === "collapsed";
  return (
    <AdminShell me={me} initialCollapsed={collapsed}>
      {children}
    </AdminShell>
  );
}
