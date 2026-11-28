/**
 * The rows of a list of forwarding codes: the GSM codes (`codes`) and the
 * North American star codes (`star_codes`, Verizon's *71 and *73) of one
 * carrier, or the top-level codes, as one list. Each row has its label in
 * the interface language, the API's description in the guide's language
 * and the code to dial.
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import { sortForwardingCodes, sortStarCodes, type CallForwardingCondition, type StarCodeCondition } from "./channels";

type GsmCode = Schema<"CallForwardingCode">;
type StarCode = Schema<"CallForwardingStarCode">;

const CONDITION_LABELS: Record<CallForwardingCondition, MessageKey> = {
  no_answer: "channels.forwarding.condition.no_answer",
  busy: "channels.forwarding.condition.busy",
  unreachable: "channels.forwarding.condition.unreachable",
  cancel_all: "channels.forwarding.condition.cancel_all",
};

const STAR_CONDITION_LABELS: Record<StarCodeCondition, MessageKey> = {
  no_answer_or_busy: "channels.forwarding.starCondition.no_answer_or_busy",
  cancel_all: "channels.forwarding.starCondition.cancel_all",
};

export interface ForwardingCodeRow {
  /** Unique within one list (a GSM and a star code may both switch forwarding off). */
  key: string;
  label: MessageKey;
  description: string;
  dialCode: string;
}

/** The GSM codes in their usual order, then the star codes; an API without star codes sends none. */
export function forwardingCodeRows(codes: readonly GsmCode[], starCodes: readonly StarCode[] = []): ForwardingCodeRow[] {
  return [
    ...sortForwardingCodes(codes).map((code) => ({
      key: `gsm-${code.condition}`,
      label: CONDITION_LABELS[code.condition],
      description: code.description,
      dialCode: code.dial_code,
    })),
    ...sortStarCodes(starCodes).map((code) => ({
      key: `star-${code.condition}`,
      label: STAR_CONDITION_LABELS[code.condition],
      description: code.description,
      dialCode: code.dial_code,
    })),
  ];
}
