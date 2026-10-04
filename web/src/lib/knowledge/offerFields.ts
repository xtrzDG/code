/**
 * The bookable part of the knowledge item form: a service's or package's
 * break after it, who performs an offer (or which rooms are of a room
 * type), and a room type's seasonal nightly rates.
 *
 * Each field belongs to some kinds only (the API refuses it on others):
 * a break to services and packages, performers to every bookable kind,
 * seasons to room types. When the owner switches an item to another kind,
 * the fields the new kind cannot have are cleared.
 */

import type { MessageKey } from "@/i18n/translate";

import { isBookableKind, kindHasBuffer, type OfferItem, type SeasonalNightlyRate } from "../offers";
import type { KnowledgeForm, KnowledgeItemCreateBody, KnowledgeItemPatchBody } from "./form";
import { MAX_SEASONS, sameRates, seasonRowsFromRates, validateSeasonRows, type SeasonRowErrors } from "./seasons";

/** A performer stays blocked 0 to 240 minutes after a service (the API's limit). */
export const MAX_BUFFER_MINUTES = 240;

export interface SeasonsProblem {
  rows: SeasonRowErrors[];
  /** The first two seasons (indexes) that share a day. */
  overlap: [number, number] | null;
  /** More seasons than the API takes. */
  tooMany?: boolean;
}

export interface OfferFieldErrors {
  buffer?: MessageKey;
  seasons?: SeasonsProblem;
}

type OfferSource = Pick<OfferItem, "buffer_minutes" | "performer_resource_ids" | "seasonal_rates">;

/** The offer fields of the editor for a stored item. */
export function offerFormFromItem(
  item: OfferSource,
  currency: string,
): Pick<KnowledgeForm, "buffer" | "performerIds" | "seasons"> {
  return {
    buffer: item.buffer_minutes ? String(item.buffer_minutes) : "",
    performerIds: [...(item.performer_resource_ids ?? [])],
    seasons: seasonRowsFromRates(item.seasonal_rates ?? [], currency),
  };
}

export function validateOfferFields(form: KnowledgeForm, currency: string): OfferFieldErrors {
  const errors: OfferFieldErrors = {};
  const buffer = form.buffer.trim();
  if (kindHasBuffer(form.kind) && buffer !== "") {
    if (!/^\d+$/.test(buffer)) {
      errors.buffer = "validation.wholeNumber";
    } else if (Number(buffer) > MAX_BUFFER_MINUTES) {
      errors.buffer = "knowledge.offer.errors.bufferRange";
    }
  }
  if (form.kind === "room_type" && form.seasons.length > 0) {
    const seasons = validateSeasonRows(form.seasons, currency);
    if (!seasons.ok) {
      errors.seasons = { rows: seasons.rows, overlap: seasons.overlap };
    } else if (form.seasons.length > MAX_SEASONS) {
      errors.seasons = { rows: [], overlap: null, tooMany: true };
    }
  }
  return errors;
}

interface OfferValues {
  buffer: number | null;
  performers: string[];
  seasons: SeasonalNightlyRate[];
}

/** What a validated form says for its own kind (fields its kind cannot have are empty). */
function offerValues(form: KnowledgeForm, currency: string): OfferValues {
  const buffer = form.buffer.trim();
  const seasons = form.kind === "room_type" ? validateSeasonRows(form.seasons, currency) : null;
  return {
    buffer: kindHasBuffer(form.kind) && buffer !== "" && Number(buffer) > 0 ? Number(buffer) : null,
    performers: isBookableKind(form.kind) ? [...new Set(form.performerIds)] : [],
    seasons: seasons?.ok ? seasons.rates : [],
  };
}

/** The offer fields of POST …/knowledge (only those the kind may have). */
export function offerCreateFields(form: KnowledgeForm, currency: string): Partial<KnowledgeItemCreateBody> {
  const values = offerValues(form, currency);
  return {
    ...(values.buffer !== null ? { buffer_minutes: values.buffer } : {}),
    ...(values.performers.length > 0 ? { performer_resource_ids: values.performers } : {}),
    ...(values.seasons.length > 0 ? { seasonal_rates: values.seasons } : {}),
  };
}

function sameIds(left: readonly string[], right: readonly string[]): boolean {
  return left.length === right.length && [...left].sort().join(",") === [...right].sort().join(",");
}

/** The offer fields of PATCH …/knowledge/{id} that changed against `initial` (null clears the break). */
export function offerPatchFields(form: KnowledgeForm, initial: KnowledgeForm, currency: string): KnowledgeItemPatchBody {
  const next = offerValues(form, currency);
  const before = offerValues(initial, currency);
  const patch: KnowledgeItemPatchBody = {};
  if (next.buffer !== before.buffer) {
    patch.buffer_minutes = next.buffer;
  }
  if (!sameIds(next.performers, before.performers)) {
    patch.performer_resource_ids = next.performers;
  }
  if (!sameRates(next.seasons, before.seasons)) {
    patch.seasonal_rates = next.seasons;
  }
  return patch;
}
