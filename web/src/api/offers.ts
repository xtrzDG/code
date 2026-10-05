"use client";

/**
 * The business's bookable offers (services, packages and room types, on
 * and off), shared by the resources page and the bookings form. They are
 * read by kind, every page of each, so a long price list is complete.
 */

import { BOOKABLE_KINDS } from "@/lib/offers";

import { api } from "./client";
import { MAX_PAGE_SIZE } from "./paging";
import { queryKeys } from "./queryKeys";
import { unwrap } from "./result";
import type { KnowledgeItemDetails } from "./types";
import { useCachedQuery } from "./useQuery";

/** A business with more offers than this is not a small business: the lists stop there. */
const MAX_PAGES_PER_KIND = 10;

async function loadKind(businessId: string, kind: KnowledgeItemDetails["kind"]): Promise<KnowledgeItemDetails[]> {
  const items: KnowledgeItemDetails[] = [];
  let cursor: string | undefined;
  for (let page = 0; page < MAX_PAGES_PER_KIND; page += 1) {
    const data = await unwrap(
      api.GET("/v1/businesses/{business_id}/knowledge", {
        params: { path: { business_id: businessId }, query: { kind, limit: String(MAX_PAGE_SIZE), cursor } },
      }),
    );
    items.push(...(data.items ?? []));
    if (!data.next_cursor) {
      break;
    }
    cursor = data.next_cursor;
  }
  return items;
}

async function loadBookableOffers(businessId: string): Promise<KnowledgeItemDetails[]> {
  const kinds = await Promise.all(BOOKABLE_KINDS.map((kind) => loadKind(businessId, kind)));
  return kinds.flat();
}

/** Every service, package and room type of the business (switched-off ones too). */
export function useBookableOffers(businessId: string, options: { enabled?: boolean } = {}) {
  return useCachedQuery(queryKeys.knowledge.offers(businessId), () => loadBookableOffers(businessId), options);
}
