"use client";

import type { BusinessMemberRole, BusinessStatus } from "@/api/types";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";

import { Badge, type BadgeTone } from "../ui/Badge";

const STATUS: Record<BusinessStatus, { tone: BadgeTone; label: MessageKey }> = {
  onboarding: { tone: "warning", label: "businesses.status.onboarding" },
  testing: { tone: "info", label: "businesses.status.testing" },
  live: { tone: "success", label: "businesses.status.live" },
  paused: { tone: "neutral", label: "businesses.status.paused" },
};

const ROLE: Record<BusinessMemberRole, MessageKey> = {
  owner: "businesses.role.owner",
  staff: "businesses.role.staff",
};

export function BusinessStatusBadge({ status }: { status: BusinessStatus }) {
  const { t } = useI18n();
  return <Badge tone={STATUS[status].tone}>{t(STATUS[status].label)}</Badge>;
}

export function MemberRoleBadge({ role }: { role: BusinessMemberRole }) {
  const { t } = useI18n();
  return <Badge tone={role === "owner" ? "accent" : "neutral"}>{t(ROLE[role])}</Badge>;
}
