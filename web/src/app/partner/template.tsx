import type { ReactNode } from "react";

import { PageTransition } from "@/components/motion/PageTransition";

/** The page rises into place when it is opened (templates remount on every navigation). */
export default function Template({ children }: { children: ReactNode }) {
  return <PageTransition>{children}</PageTransition>;
}
