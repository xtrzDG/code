"use client";

import type { ReactNode } from "react";

import { BusinessShell } from "@/components/shell/BusinessShell";

import { useSectionPrefetch } from "./useSectionPrefetch";

/** The business frame, loading a page's first data ahead of the click. */
export function BusinessFrame({ children, initialCollapsed }: { children: ReactNode; initialCollapsed: boolean }) {
  return (
    <BusinessShell prefetch={useSectionPrefetch()} initialCollapsed={initialCollapsed}>
      {children}
    </BusinessShell>
  );
}
