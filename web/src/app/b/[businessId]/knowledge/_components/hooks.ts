"use client";

import { useMemo } from "react";

import { api } from "@/api/client";
import { useApiQuery } from "@/api/hooks";
import type { KnowledgeItemKind } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";
import type { MessageKey } from "@/i18n/translate";
import { orderKinds } from "@/lib/knowledge/kinds";

/** The business niche (knowledge kinds, resource kind, booking unit), in the UI language. */
export function useNicheDetails() {
  const { business } = useBusiness();
  const { locale } = useI18n();
  return useApiQuery(
    () =>
      api.GET("/v1/catalog/niches/{niche_key}", {
        params: { path: { niche_key: business.niche_key }, query: { language: locale } },
      }),
    [business.niche_key, locale],
  );
}

/** Knowledge kinds with the niche's own kinds first. */
export function useKnowledgeKinds(): KnowledgeItemKind[] {
  const niche = useNicheDetails();
  const nicheKinds = niche.data?.knowledge_kinds;
  return useMemo(() => orderKinds(nicheKinds), [nicheKinds]);
}

/** One item of a kind (for the editor). */
export const KIND_LABELS: Record<KnowledgeItemKind, MessageKey> = {
  faq: "onboarding.offer.kinds.faq",
  policy: "onboarding.offer.kinds.policy",
  menu_item: "onboarding.offer.kinds.menu_item",
  service: "onboarding.offer.kinds.service",
  room_type: "onboarding.offer.kinds.room_type",
  package: "onboarding.offer.kinds.package",
  vehicle: "onboarding.offer.kinds.vehicle",
  product: "onboarding.offer.kinds.product",
};

/** A group of items of a kind (list headings and filters). */
export const KIND_GROUP_LABELS: Record<KnowledgeItemKind, MessageKey> = {
  faq: "knowledge.kindGroups.faq",
  policy: "knowledge.kindGroups.policy",
  menu_item: "knowledge.kindGroups.menu_item",
  service: "knowledge.kindGroups.service",
  room_type: "knowledge.kindGroups.room_type",
  package: "knowledge.kindGroups.package",
  vehicle: "knowledge.kindGroups.vehicle",
  product: "knowledge.kindGroups.product",
};
