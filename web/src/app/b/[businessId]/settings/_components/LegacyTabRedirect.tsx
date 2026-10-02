"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { decodeHash } from "@/components/workspace/helpers";
import { businessPath, type BusinessPage } from "@/lib/navigation";

/** The tabs that lived in the hash of /settings before they got their own pages. */
const HASH_PAGES: Record<string, BusinessPage> = {
  general: "settings",
  team: "settings/team",
  notifications: "settings/notifications",
  privacy: "settings/privacy",
  audit: "settings/audit",
  billing: "settings/billing",
};

/**
 * Old links such as /settings#team (a hash never reaches the server, so
 * next.config's redirects cannot see it) open the tab's own page.
 */
export function LegacyTabRedirect() {
  const router = useRouter();
  const { business } = useBusiness();

  useEffect(() => {
    const page = HASH_PAGES[decodeHash(window.location.hash)];
    if (page && page !== "settings") {
      router.replace(businessPath(business.id, page));
    }
  }, [router, business.id]);

  return null;
}
