/**
 * How a customer source tag reads in the owner's language: the share
 * card's place ("Table (QR code)"), the line called ("Call to +995 …"), an
 * ad, or the tag itself. Shared by Reports and the inbox's source chip.
 */

import type { Translator } from "@/i18n/translate";
import { formatPhone } from "@/lib/phone";

import { sourceNameOf } from "./sourcesModel";

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
