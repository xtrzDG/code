"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import type { MemberRole } from "@/lib/sections";

/** The viewer's role for the navigation: owners and platform admins see everything, staff their part. */
export function useMemberRole(): MemberRole {
  const { isOwner, isPlatformAdmin } = useBusiness();
  return isOwner || isPlatformAdmin ? "owner" : "staff";
}
