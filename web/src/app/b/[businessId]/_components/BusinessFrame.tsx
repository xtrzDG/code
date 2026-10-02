"use client";

import type { ReactNode } from "react";

import { BusinessShell } from "@/components/shell/BusinessShell";

import { useSectionPrefetch } from "./useSectionPrefetch";

/** The business sidebar, loading a section's first data ahead of the click. */
export function BusinessFrame({ children }: { children: ReactNode }) {
  return <BusinessShell prefetch={useSectionPrefetch()}>{children}</BusinessShell>;
}
