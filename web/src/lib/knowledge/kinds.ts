/**
 * Pure helpers of the Knowledge section (app/b/[businessId]/knowledge):
 * item kinds, filtering, grouping, sorting and counting items.
 */

import type { KnowledgeItemDetails, KnowledgeItemKind } from "@/api/types";

/** Every kind, in the order the API lists them. */
const KNOWLEDGE_KINDS: readonly KnowledgeItemKind[] = [
  "menu_item",
  "service",
  "room_type",
  "package",
  "vehicle",
  "product",
  "faq",
  "policy",
];

/** The niche's kinds first (in its order), then every other kind. */
export function orderKinds(nicheKinds: readonly KnowledgeItemKind[] | undefined): KnowledgeItemKind[] {
  const first = (nicheKinds ?? []).filter((kind, index, list) => list.indexOf(kind) === index);
  return [...first, ...KNOWLEDGE_KINDS.filter((kind) => !first.includes(kind))];
}

/** Every business may keep questions and rules, whatever its niche (the API's rule). */
const ALWAYS_ALLOWED_KINDS: readonly KnowledgeItemKind[] = ["faq", "policy"];

/**
 * The kinds a business may add: its niche's (in their order), then
 * questions and rules. The API refuses other kinds (a salon has no room
 * types). Every kind while the niche is not known yet.
 */
export function allowedKinds(nicheKinds: readonly KnowledgeItemKind[] | undefined): KnowledgeItemKind[] {
  if (!nicheKinds) {
    return [...KNOWLEDGE_KINDS];
  }
  return [...nicheKinds, ...ALWAYS_ALLOWED_KINDS].filter((kind, index, list) => list.indexOf(kind) === index);
}

/** Questions and rules have no price; everything sold does. */
export function kindHasPrice(kind: KnowledgeItemKind): boolean {
  return kind !== "faq" && kind !== "policy";
}

/** Kinds that usually last a while (a haircut, a VR hour, a car for a day). */
export function kindHasDuration(kind: KnowledgeItemKind): boolean {
  return kind === "service" || kind === "package" || kind === "vehicle";
}

export type KnowledgeStatusFilter = "all" | "active" | "inactive";

export interface KnowledgeFilter {
  kind: KnowledgeItemKind | "all";
  status: KnowledgeStatusFilter;
}

export function filterKnowledgeItems<T extends Pick<KnowledgeItemDetails, "kind" | "is_active">>(
  items: readonly T[],
  filter: KnowledgeFilter,
): T[] {
  return items.filter(
    (item) =>
      (filter.kind === "all" || item.kind === filter.kind) &&
      (filter.status === "all" || (filter.status === "active") === item.is_active),
  );
}

export interface KnowledgeGroup<T> {
  kind: KnowledgeItemKind;
  items: T[];
}

/** Non-empty groups in `kindOrder`; items keep their order inside a group. */
export function groupByKind<T extends Pick<KnowledgeItemDetails, "kind">>(
  items: readonly T[],
  kindOrder: readonly KnowledgeItemKind[],
): KnowledgeGroup<T>[] {
  const order = [...kindOrder, ...KNOWLEDGE_KINDS.filter((kind) => !kindOrder.includes(kind))];
  const groups = new Map<KnowledgeItemKind, T[]>();
  for (const item of items) {
    const list = groups.get(item.kind) ?? [];
    list.push(item);
    groups.set(item.kind, list);
  }
  return order.flatMap((kind) => {
    const list = groups.get(kind);
    return list && list.length > 0 ? [{ kind, items: list }] : [];
  });
}

/** Items by title in the UI language (the API's order), e.g. after adding one locally. */
export function sortByTitle<T extends Pick<KnowledgeItemDetails, "title">>(items: readonly T[], locale: string): T[] {
  return [...items].sort((left, right) => left.title.localeCompare(right.title, locale, { sensitivity: "base" }));
}

export function countByKind(items: readonly Pick<KnowledgeItemDetails, "kind">[]): Partial<Record<KnowledgeItemKind, number>> {
  const counts: Partial<Record<KnowledgeItemKind, number>> = {};
  for (const item of items) {
    counts[item.kind] = (counts[item.kind] ?? 0) + 1;
  }
  return counts;
}

/**
 * A list after one item was saved (edited, switched on or off, or added):
 * it stays, in place, only while it matches the list's filter; a new one
 * that matches goes first.
 */
export function withSavedItem<T extends Pick<KnowledgeItemDetails, "id" | "kind" | "is_active">>(
  list: readonly T[],
  saved: T,
  filter: KnowledgeFilter,
): T[] {
  const others = list.filter((item) => item.id !== saved.id);
  if (filterKnowledgeItems([saved], filter).length === 0) {
    return others;
  }
  const exists = others.length < list.length;
  return exists ? list.map((item) => (item.id === saved.id ? saved : item)) : [saved, ...list];
}
