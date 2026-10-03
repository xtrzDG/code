import type { UserView } from "@/api/types";
import { cn } from "@/lib/cn";

type UserNames = Pick<UserView, "display_name" | "phone_number" | "email">;

/** Name to show for the signed-in user: display name, else phone or e-mail. */
export function userDisplayName(user: UserNames): string {
  return user.display_name || user.phone_number || user.email || "";
}

/** How the user signs in: the phone number, else the e-mail. */
export function userContact(user: UserNames): string {
  return user.phone_number || user.email || "";
}

/** Up to two letters of the name ("Nino Beridze" -> "NB"), or the first digit-free character. */
export function userInitials(user: UserNames): string {
  const words = (user.display_name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length > 0) {
    return words
      .slice(0, 2)
      .map((word) => Array.from(word)[0] ?? "")
      .join("")
      .toLocaleUpperCase();
  }
  const fallback = (user.email ?? "").trim();
  return fallback ? (Array.from(fallback)[0] ?? "").toLocaleUpperCase() : "#";
}

/** A round badge with the user's initials on the accent gradient. */
export function UserAvatar({ user, className }: { user: UserNames; className?: string }) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--accent-solid),color-mix(in_oklab,var(--accent-solid)_55%,var(--tone-sand)))] text-xs font-semibold text-on-accent shadow-[inset_0_0_0_1px_rgb(255_255_255/0.2)]",
        className,
      )}
    >
      {userInitials(user)}
    </span>
  );
}
