import type { ReactNode } from "react";

import { PageTransition } from "@/components/motion/PageTransition";

/** Each page of the help center rises into place when it is opened. */
export default function Template({ children }: { children: ReactNode }) {
  return <PageTransition>{children}</PageTransition>;
}
