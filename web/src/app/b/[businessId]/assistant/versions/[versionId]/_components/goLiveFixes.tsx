"use client";

/** Where and how an owner fixes what stops a version from going live. */

import Link from "next/link";
import type { ReactNode } from "react";

import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import type { GoLiveCheckCode } from "@/lib/assistant/goLive";
import { businessPath } from "@/lib/navigation";

type ProfileGapKind = Schema<"ProfileGapKind">;

export const GAP_KIND_LABELS: Record<ProfileGapKind, MessageKey> = {
  missing_required_answer: "assistant.gapKinds.missing_required_answer",
  no_opening_hours: "assistant.gapKinds.no_opening_hours",
  no_address: "assistant.gapKinds.no_address",
  no_handoff_contact: "assistant.gapKinds.no_handoff_contact",
  no_booking_rules: "assistant.gapKinds.no_booking_rules",
  no_resources: "assistant.gapKinds.no_resources",
  no_priced_items: "assistant.gapKinds.no_priced_items",
  no_faq: "assistant.gapKinds.no_faq",
  unanswered_question: "assistant.gapKinds.unanswered_question",
};

function isGapKind(value: string): value is ProfileGapKind {
  return value in GAP_KIND_LABELS;
}

/** Where an owner fixes each launch condition. */
export function useFixLinks(): Partial<Record<GoLiveCheckCode, { href: string; label: MessageKey }>> {
  const { business } = useBusiness();
  return {
    subscription_or_trial: { href: businessPath(business.id, "billing"), label: "assistant.checklist.fixBilling" },
    dpa: { href: `${businessPath(business.id, "settings")}#privacy`, label: "assistant.checklist.fixDpa" },
    profile_gaps: { href: businessPath(business.id, "onboarding"), label: "assistant.checklist.fixProfile" },
    staff_contact: { href: `${businessPath(business.id, "settings")}#notifications`, label: "assistant.checklist.fixStaffContact" },
  };
}

export function FixLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
      {children}
    </Link>
  );
}

export function ActionButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} className="text-sm font-medium whitespace-nowrap text-accent hover:underline">
      {children}
    </button>
  );
}

export function GapList({ kinds }: { kinds: readonly string[] }) {
  const { t } = useI18n();
  return (
    <ul className="mt-1 list-disc pl-5">
      {kinds.map((kind) => (
        <li key={kind}>{isGapKind(kind) ? t(GAP_KIND_LABELS[kind]) : kind}</li>
      ))}
    </ul>
  );
}
