/**
 * Pure rules of the team in the inbox: a member's name (the display name
 * from the inbox, else what the business view knows), initials, a stable
 * avatar tone per person, and how a member reads in the assign menu.
 */

import type { BusinessMemberRole } from "@/api/types";

import { initialsOf } from "./conversationModel";
import type { InboxAssigneeView } from "./types";

export interface TeamMember {
  userId: string;
  /** The name to show, null when nobody knows one (shown as "Team member"). */
  name: string | null;
  initials: string;
  role: BusinessMemberRole;
  /** Conversations waiting for the team this person handles now. */
  awaitingCount: number;
  isMe: boolean;
  /** One of AVATAR_TONES, the same for a person everywhere. */
  tone: number;
}

interface KnownMember {
  user_id: string;
  display_name?: string | null;
  email?: string | null;
  phone_number?: string | null;
}

/** How many avatar colours there are (tokens --chart-1..3 and the accent). */
export const AVATAR_TONE_COUNT = 4;

/** The same small number for the same id: avatars keep their colour across pages. */
export function avatarTone(userId: string): number {
  let hash = 0;
  for (const character of userId) {
    hash = (hash * 31 + (character.codePointAt(0) ?? 0)) >>> 0;
  }
  return hash % AVATAR_TONE_COUNT;
}

function knownName(member: KnownMember | undefined): string | null {
  if (!member) {
    return null;
  }
  return member.display_name || member.email?.split("@")[0] || member.phone_number || null;
}

/** The assignees as the inbox shows them: owners first, then by name, me among them. */
export function teamMembers(
  assignees: readonly InboxAssigneeView[],
  businessMembers: readonly KnownMember[],
  myUserId: string,
): TeamMember[] {
  const members = assignees.map((assignee): TeamMember => {
    const name = assignee.display_name || knownName(businessMembers.find((member) => member.user_id === assignee.user_id));
    return {
      userId: assignee.user_id,
      name,
      initials: initialsOf(name),
      role: assignee.role,
      awaitingCount: assignee.awaiting_count,
      isMe: assignee.user_id === myUserId,
      tone: avatarTone(assignee.user_id),
    };
  });
  return members.sort((left, right) => {
    if (left.role !== right.role) {
      return left.role === "owner" ? -1 : 1;
    }
    return (left.name ?? "").localeCompare(right.name ?? "");
  });
}

/** Me first in the menu, then the rest in team order. */
export function menuOrder(members: readonly TeamMember[]): TeamMember[] {
  return [...members.filter((member) => member.isMe), ...members.filter((member) => !member.isMe)];
}

/**
 * Who may change the assignment: owners always; staff may give a
 * conversation nobody or they themselves handle to anyone, not take over a
 * colleague's (the API refuses that with `assigned_to_colleague`).
 */
export function canReassign(isOwner: boolean, assigneeUserId: string | null | undefined, myUserId: string): boolean {
  return isOwner || !assigneeUserId || assigneeUserId === myUserId;
}
