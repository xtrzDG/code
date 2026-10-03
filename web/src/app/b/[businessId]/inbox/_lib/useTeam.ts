"use client";

/**
 * The team of the business as the inbox shows it: names and initials for
 * the assignees on rows and in the assign menu, with each member's current
 * workload (GET …/inbox/assignees: no phone or e-mail, not audited, kept
 * fresh by the live stream like the counts).
 */

import { useCallback, useMemo } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

import { teamMembers, type TeamMember } from "./team";

export interface Team {
  /** Owners first, then by name; undefined while loading. */
  members: readonly TeamMember[] | undefined;
  /** The member with this id (a former member: null). */
  find: (userId: string | null | undefined) => TeamMember | null;
  isLoading: boolean;
  reload: () => void;
}

export function useTeam(): Team {
  const { business, me } = useBusiness();
  const assignees = useQuery(queryKeys.inbox.assignees(business.id), () =>
    api.GET("/v1/businesses/{business_id}/inbox/assignees", { params: { path: { business_id: business.id } } }),
  );
  const items = assignees.data?.items;
  const members = useMemo(
    () => (items ? teamMembers(items, business.members, me.user.id) : undefined),
    [items, business.members, me.user.id],
  );
  const find = useCallback(
    (userId: string | null | undefined) => (userId ? (members?.find((member) => member.userId === userId) ?? null) : null),
    [members],
  );
  return { members, find, isLoading: assignees.isLoading, reload: assignees.reload };
}

export type { TeamMember };
