/**
 * A customer's standing as one line: "Regular customer · 4 visits", or
 * the standing alone before the first visit ("New customer").
 */

import type { Schema } from "@/api/types";
import type { MessageKey, Translator } from "@/i18n/translate";

export type CustomerStanding = Schema<"CustomerStanding">;

export const STANDING_LABELS: Record<CustomerStanding, MessageKey> = {
  new: "customers.standing.new",
  returning: "customers.standing.returning",
  visited: "customers.standing.visited",
  regular: "customers.standing.regular",
};

export function standingLine(
  translator: Pick<Translator, "t" | "tp">,
  standing: CustomerStanding,
  visitCount: number,
): string {
  const label = translator.t(STANDING_LABELS[standing]);
  if (visitCount <= 0) {
    return label;
  }
  return translator.t("customers.standing.line", {
    standing: label,
    visits: translator.tp("customers.standing.visits", visitCount),
  });
}
