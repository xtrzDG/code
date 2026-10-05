import { cn } from "@/lib/cn";

import { userInitials, type UserNames } from "./userNames";

export { userContact, userDisplayName, userInitials } from "./userNames";

/** A round badge with the user's initials on the accent gradient (user content: letters of their name). */
export function UserAvatar({ user, className }: { user: UserNames; className?: string }) {
  return (
    <span
      aria-hidden
      data-user-content
      className={cn(
        "inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent-solid),color-mix(in_oklab,var(--accent-solid)_55%,var(--tone-sand)))] text-xs font-semibold text-on-accent shadow-[inset_0_0_0_1px_rgb(255_255_255/0.2)]",
        className,
      )}
    >
      {userInitials(user)}
    </span>
  );
}
