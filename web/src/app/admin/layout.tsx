import { notFound } from "next/navigation";

import { AdminShell } from "@/components/shell/AdminShell";
import { getCurrentUser } from "@/server/api";

/** /admin/* is only for platform admins; everyone else gets a 404. */
export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  const me = await getCurrentUser();
  if (!me.user.is_platform_admin) {
    notFound();
  }
  return <AdminShell me={me}>{children}</AdminShell>;
}
