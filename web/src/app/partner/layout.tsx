import { notFound } from "next/navigation";

import { TopBar } from "@/components/shell/TopBar";
import { getCurrentUser } from "@/server/api";

/**
 * /partner is only for partners (everyone else gets a 404). The check runs in
 * the layout, above the loading boundary, so the 404 is the response's status.
 */
export default async function PartnerLayout({ children }: LayoutProps<"/partner">) {
  const me = await getCurrentUser();
  if (!me.is_partner) {
    notFound();
  }
  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      {children}
    </div>
  );
}
