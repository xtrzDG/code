"use client";

import { useEffect } from "react";

import { titleWithCount } from "@/lib/inboxBadges";

/**
 * Keeps "(3) " in front of the browser tab's title while things wait for a
 * person, also after a navigation sets a new title; the bare title comes
 * back when nothing waits or the business is left.
 */
export function useDocumentTitleCount(count: number): void {
  useEffect(() => {
    const apply = () => {
      const next = titleWithCount(document.title, count);
      if (next !== document.title) {
        document.title = next;
      }
    };
    apply();
    const observer = new MutationObserver(apply);
    observer.observe(document.head, { subtree: true, childList: true, characterData: true });
    return () => {
      observer.disconnect();
      document.title = titleWithCount(document.title, 0);
    };
  }, [count]);
}
