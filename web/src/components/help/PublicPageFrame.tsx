import type { ReactNode } from "react";

import { TopBar } from "@/components/shell/TopBar";
import { hasSession } from "@/server/api";

/**
 * The frame of the public help and status pages: the top bar (with sign
 * out for someone signed in) and the page. Anyone may read them, signed in
 * or not.
 */
export async function PublicPageFrame({ children }: { children: ReactNode }) {
  const signedIn = await hasSession();
  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar signedIn={signedIn} />
      <main id="main" className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 lg:py-12">
        {children}
      </main>
    </div>
  );
}
