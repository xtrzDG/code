"use client";

/**
 * Who handles the conversation: a button with the assignee's avatar (or
 * "Assign") that opens a menu of the team, me first, each with how many
 * waiting conversations they handle now. Staff may take or hand on a
 * conversation nobody (or they) handle; only an owner takes over a
 * colleague's. Arrow keys move in the menu, Escape closes it.
 */

import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconCheck, IconChevronDown, IconUsers } from "@/components/icons";
import { Spinner, UserContent } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import { canReassign, menuOrder, type TeamMember } from "../../_lib/team";
import type { ConversationAssignmentView } from "../../_lib/types";
import { useAssign } from "../../_lib/useAssign";
import type { Team } from "../../_lib/useTeam";
import { MemberAvatar } from "../MemberAvatar";

export function AssignMenu({
  conversationId,
  assignment,
  team,
}: {
  conversationId: string;
  assignment: ConversationAssignmentView;
  team: Team;
}) {
  const { t, tp } = useI18n();
  const { me, isOwner } = useBusiness();
  const id = useId();
  const [isOpen, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { assign, isPending } = useAssign(conversationId);
  const assignee = team.find(assignment.assignee_user_id);
  const mayChange = canReassign(isOwner, assignment.assignee_user_id, me.user.id);
  const nameOf = (member: TeamMember) => (member.isMe ? t("inbox.assign.you") : (member.name ?? t("inbox.assign.teammate")));
  // On the screen a teammate's own name is user content; "You" and "Team member" are the interface's.
  const shownName = (member: TeamMember) => (!member.isMe && member.name ? <UserContent>{member.name}</UserContent> : nameOf(member));

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointer);
    menuRef.current?.querySelector<HTMLElement>('[role^="menuitem"]:not([aria-disabled="true"])')?.focus();
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [isOpen]);

  const choose = (member: TeamMember | null) => {
    setOpen(false);
    void assign(assignment, member);
  };

  const onMenuKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = [...(menuRef.current?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? [])];
    const index = items.indexOf(document.activeElement as HTMLElement);
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      rootRef.current?.querySelector("button")?.focus();
    } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const step = event.key === "ArrowDown" ? 1 : -1;
      items[(index + step + items.length) % items.length]?.focus();
    }
  };

  const label = assignee
    ? assignee.isMe
      ? t("inbox.assign.handledByYou")
      : t("inbox.assign.handledBy", { name: nameOf(assignee) })
    : assignment.assignee_user_id
      ? t("inbox.assign.handledBy", { name: t("inbox.assign.teammate") })
      : t("inbox.assign.nobody");

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((open) => !open)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? `${id}-menu` : undefined}
        aria-label={`${label}. ${t("inbox.assign.menuLabel")}`}
        className="motion-press flex h-10 cursor-pointer items-center gap-1.5 rounded-full border border-line bg-surface px-1.5 text-sm text-ink hover:border-line-strong sm:max-w-56 sm:pe-2.5"
      >
        {isPending ? (
          <Spinner size="sm" />
        ) : assignee ? (
          <MemberAvatar member={assignee} size="sm" />
        ) : (
          <span className="flex size-7 items-center justify-center rounded-full border border-dashed border-line-strong text-ink-subtle">
            <IconUsers className="size-4" aria-hidden />
          </span>
        )}
        {/* On phones the avatar alone: the customer's name needs the room. */}
        <span className="hidden min-w-0 truncate sm:inline" aria-hidden>
          {assignee ? shownName(assignee) : t("inbox.assign.open")}
        </span>
        <IconChevronDown className="hidden size-4 shrink-0 text-ink-subtle sm:block" aria-hidden />
      </button>

      {isOpen ? (
        <div
          ref={menuRef}
          id={`${id}-menu`}
          role="menu"
          aria-label={t("inbox.assign.menuLabel")}
          onKeyDown={onMenuKey}
          className="animate-settle absolute end-0 top-full z-30 mt-2 w-72 max-w-[calc(100vw-2rem)] overflow-hidden rounded-2xl border border-line bg-surface py-1.5 shadow-2xl"
        >
          <p className="px-4 pt-1.5 pb-2 text-xs font-medium text-ink-subtle">
            {assignment.is_assigned_automatically ? t("inbox.assign.automatically") : t("inbox.assign.menuLabel")}
          </p>
          {!mayChange ? <p className="px-4 pb-2 text-sm text-ink-muted">{t("inbox.assign.colleague")}</p> : null}
          {team.members === undefined ? (
            <p className="flex items-center gap-2 px-4 py-2 text-sm text-ink-muted" role="status">
              <Spinner size="sm" /> {t("inbox.assign.loading")}
            </p>
          ) : (
            menuOrder(team.members).map((member) => {
              const isCurrent = member.userId === assignment.assignee_user_id;
              return (
                <button
                  key={member.userId}
                  type="button"
                  role="menuitemradio"
                  aria-checked={isCurrent}
                  aria-disabled={!mayChange || undefined}
                  tabIndex={-1}
                  onClick={() => (mayChange && !isCurrent ? choose(member) : setOpen(false))}
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-2.5 text-start text-sm outline-none focus-visible:bg-surface-muted",
                    mayChange ? "cursor-pointer hover:bg-surface-muted" : "cursor-not-allowed opacity-60",
                  )}
                >
                  <MemberAvatar member={member} size="md" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium text-ink">
                      {member.isMe ? `${t("inbox.assign.takeIt")} (${t("inbox.assign.you")})` : shownName(member)}
                    </span>
                    <span className="block text-xs text-ink-subtle">
                      {t(member.role === "owner" ? "businesses.role.owner" : "businesses.role.staff")}
                      {" · "}
                      {tp("inbox.assign.waiting", member.awaitingCount)}
                    </span>
                  </span>
                  {isCurrent ? <IconCheck className="size-4 shrink-0 text-accent" aria-hidden /> : null}
                </button>
              );
            })
          )}
          {assignment.assignee_user_id && mayChange ? (
            <button
              type="button"
              role="menuitem"
              tabIndex={-1}
              onClick={() => choose(null)}
              className="mt-1 flex w-full cursor-pointer items-center gap-3 border-t border-line px-4 py-2.5 text-start text-sm text-ink-muted outline-none hover:bg-surface-muted focus-visible:bg-surface-muted"
            >
              {t("inbox.assign.unassign")}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
