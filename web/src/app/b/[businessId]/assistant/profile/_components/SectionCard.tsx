"use client";

/**
 * One card of Assistant → Business profile: the section's name and icon,
 * a line of what it holds now, and how much is left to add (or that it is
 * complete). The whole card opens the section's editor.
 */

import Link from "next/link";
import { useId, type ComponentType, type SVGProps } from "react";

import { IconAlert, IconBook, IconBuilding, IconCheck, IconChevronRight, IconClock, IconMapPin, IconTag, IconUsers } from "@/components/icons";
import { Badge, Skeleton, UserSentence } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { interpolate } from "@/i18n/translate";
import type { SentenceWithUserValues } from "@/i18n/userValues";
import type { ProfileSection, SectionGaps } from "@/lib/profile/sections";

const ICONS: Record<ProfileSection, ComponentType<SVGProps<SVGSVGElement>>> = {
  business: IconBuilding,
  place: IconMapPin,
  offer: IconTag,
  hours: IconClock,
  people: IconUsers,
  rules: IconBook,
};

function GapBadge({ gaps }: { gaps: SectionGaps | undefined }) {
  const { tp, t } = useI18n();
  if (!gaps) {
    return null;
  }
  if (gaps.blocking > 0) {
    return (
      <Badge tone="danger" icon={<IconAlert className="size-3.5" aria-hidden />}>
        {tp("profileEdit.gaps.required", gaps.blocking)}
      </Badge>
    );
  }
  if (gaps.advice > 0) {
    return <Badge tone="warning">{tp("profileEdit.gaps.advice", gaps.advice)}</Badge>;
  }
  return (
    <Badge tone="success" icon={<IconCheck className="size-3.5" aria-hidden />}>
      {t("profileEdit.gaps.complete")}
    </Badge>
  );
}

export function SectionCard({
  section,
  href,
  summary,
  gaps,
}: {
  section: ProfileSection;
  href: string;
  /** What the section holds (null: loading); the business's own words in it are user content. */
  summary: SentenceWithUserValues | null;
  gaps: SectionGaps | undefined;
}) {
  const { t } = useI18n();
  const describedBy = useId();
  const Icon = ICONS[section];
  const title = t(`profileEdit.sections.${section}.title`);
  return (
    <Link
      href={href}
      aria-label={t("profileEdit.open", { section: title })}
      aria-describedby={describedBy}
      className="group motion-lift flex h-full min-w-0 flex-col gap-4 rounded-2xl border border-line bg-surface p-5 transition-colors hover:border-line-strong focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      <div className="flex items-start gap-3">
        <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent" aria-hidden>
          <Icon className="size-5" />
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <h3 className="text-[0.9375rem] font-semibold tracking-tight text-ink">{title}</h3>
          <div id={describedBy} className="text-sm text-ink-muted">
            {summary === null ? (
              <Skeleton className="mt-1.5 h-3.5 w-40" />
            ) : (
              // A preview of what the section holds: two lines at most, the whole of it in the tooltip and for screen readers.
              <p data-clip="content" title={interpolate(summary.text, summary.values)} className="line-clamp-2 break-words">
                <UserSentence {...summary} />
              </p>
            )}
          </div>
        </div>
        <IconChevronRight className="mt-2.5 size-4 shrink-0 text-ink-subtle transition-transform group-hover:translate-x-0.5 rtl:-scale-x-100 rtl:group-hover:-translate-x-0.5" aria-hidden />
      </div>
      <div className="mt-auto flex min-h-6 items-center">
        <GapBadge gaps={gaps} />
      </div>
    </Link>
  );
}
