import { TopBar } from "@/components/shell/TopBar";
import { getCurrentUser } from "@/server/api";

import { BrandsProvider } from "./_components/BrandsContext";

/**
 * /brands: chains of locations run as one. The signed-in person's
 * memberships (with their brands) come from the server once, for the
 * pages that offer a business to start or grow a brand.
 */
export default async function BrandsLayout({ children }: LayoutProps<"/brands">) {
  const me = await getCurrentUser();
  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn />
      <BrandsProvider memberships={me.memberships ?? []} userId={me.user.id}>
        {children}
      </BrandsProvider>
    </div>
  );
}
