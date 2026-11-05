"use client";

/**
 * What the analysis cards of /admin/clients/[businessId] say in their
 * folded row on a phone (PhoneFold): how many of the team are signed in,
 * the median wait, the share of replies the guard held back, the judge's
 * 30-day average and the period's margin, in the danger or warning colour
 * when the card itself raises it (replies held back often or probing, a
 * dropping score, a loss). No figure yet: the row says its name only.
 */

import type { ReactNode } from "react";

import { useI18n } from "@/i18n/client";
import { formatScore } from "@/lib/assistant/autotests";
import { formatMoney, formatNumber } from "@/lib/format";

import type { AdminClientSummary } from "../../_lib/clients";
import { guardFigures, isHeldBackOften, isProbed } from "../../_lib/replyGuard";
import { useClientMembers, useClientQuality } from "../../_lib/useClientCards";
import { foldNote as noted } from "../foldNote";
import { useWaitText } from "./ReplySpeedCard";

export interface ClientFolds {
  sessions: ReactNode;
  replySpeed: ReactNode;
  replyGuard: ReactNode;
  quality: ReactNode;
  cost: ReactNode;
}

export function useClientFolds(businessId: string, summary: AdminClientSummary): ClientFolds {
  const { t, tp, locale } = useI18n();
  const wait = useWaitText();
  const members = useClientMembers(businessId).data;
  const quality = useClientQuality(businessId).data;

  const speed = summary.reply_speed;
  const guard = guardFigures(summary.guard_activity);
  const margin = summary.cost.margin;
  const signedIn = members?.items.filter((member) => member.live_session_count > 0).length;
  const average = quality && quality.sample_count > 0 ? quality.average_score : null;

  return {
    sessions: signedIn === undefined ? null : tp("adminSessions.signedIn", signedIn),
    replySpeed: speed && speed.reply_count > 0 ? t("adminReplySpeed.fold", { wait: wait(speed.p50_ms) }) : null,
    replyGuard:
      guard.heldBackShare === null
        ? null
        : noted(
            t("adminReplyGuard.fold", {
              share: formatNumber(guard.heldBackShare, locale, { style: "percent", maximumFractionDigits: 0 }),
            }),
            isHeldBackOften(guard) || isProbed(guard) ? "danger" : null,
          ),
    quality:
      average === null || average === undefined
        ? null
        : noted(t("quality.admin.scoreValue", { score: formatScore(average, locale) }), quality?.is_dropping ? "warning" : null),
    cost: margin
      ? noted(
          t("admin.detail.marginFold", { margin: formatMoney(margin.amount_minor, margin.currency_code, locale) }),
          margin.amount_minor < 0 ? "danger" : null,
        )
      : null,
  };
}
