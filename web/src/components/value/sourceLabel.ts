/**
 * How a customer source tag reads in the owner's language: the share
 * card's place ("Table (QR code)"), the line called ("Call to +995 …"), an
 * ad, or the tag itself. Shared by Reports, the inbox's source chip and a
 * brand's overview.
 */

import { CHANNEL_LABELS } from "@/components/insights/labels";
import type { Translator } from "@/i18n/translate";
import { formatPhone } from "@/lib/phone";

import { sourceNameOf, type CustomerSourceRow } from "./sourcesModel";

export function sourceLabel(tag: string, t: Translator["t"]): string {
  const name = sourceNameOf(tag);
  switch (name.kind) {
    case "place":
      return t(name.key);
    case "phone":
      return t("sources.phone", { number: formatPhone(name.number) });
    case "ad":
      return name.id === null ? t("sources.ad") : t("sources.adWithId", { id: name.id });
    case "tag":
      return name.tag;
  }
}

/**
 * The name of a row of "Where customers came from": its tag's name, the
 * channels of the conversations that came without a tag, or "N more tags"
 * for the smallest ones folded together.
 */
export function sourceRowName(row: CustomerSourceRow, t: Translator["t"], tp: Translator["tp"]): string {
  if (row.kind === "other") {
    return tp("sources.other", row.source_count ?? 1);
  }
  if (row.kind === "untagged" || !row.acquisition_source) {
    return sourceChannels(row, t) || t("sources.untagged");
  }
  return sourceLabel(row.acquisition_source, t);
}

/** The channels a source's conversations came through, by name. */
export function sourceChannels(row: CustomerSourceRow, t: Translator["t"]): string {
  return (row.channels ?? []).map((channel) => t(CHANNEL_LABELS[channel])).join(", ");
}
