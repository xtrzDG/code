import { cn } from "@/lib/cn";

import type { TeamMember } from "../_lib/team";

/** Each tone is a token, so avatars follow the theme. */
const TONES = [
  "bg-[linear-gradient(135deg,var(--accent-solid),color-mix(in_oklab,var(--accent-solid)_55%,var(--tone-sand)))]",
  "bg-[linear-gradient(135deg,var(--chart-1),color-mix(in_oklab,var(--chart-1)_60%,var(--tone-rose)))]",
  "bg-[linear-gradient(135deg,var(--chart-2),color-mix(in_oklab,var(--chart-2)_60%,var(--ink-subtle)))]",
  "bg-[linear-gradient(135deg,var(--chart-3),color-mix(in_oklab,var(--chart-3)_60%,var(--tone-sand)))]",
] as const;

const SIZES = { xs: "size-5 text-[0.625rem]", sm: "size-7 text-[0.6875rem]", md: "size-9 text-xs" } as const;

/** A teammate's initials on their own colour (decorative: the name is always said in text). */
export function MemberAvatar({
  member,
  size = "sm",
  className,
}: {
  member: Pick<TeamMember, "initials" | "tone">;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white shadow-[inset_0_0_0_1px_rgb(255_255_255/0.22)]",
        TONES[member.tone % TONES.length],
        SIZES[size],
        className,
      )}
    >
      {member.initials}
    </span>
  );
}
