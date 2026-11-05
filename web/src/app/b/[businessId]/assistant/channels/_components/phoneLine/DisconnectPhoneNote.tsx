"use client";

/**
 * What turning the phone channel off means, in its confirm dialog: switch
 * off call forwarding on the venue's phone; and when the business rents a
 * number from us, that the number goes back to the carrier for good.
 */

import { useBusiness } from "@/components/business/BusinessContext";
import { useI18n } from "@/i18n/client";

import { numberInText } from "../../_lib/phoneLine";
import { usePhoneLine } from "../../_lib/usePhoneLine";

export function DisconnectPhoneNote() {
  const { t } = useI18n();
  const { business } = useBusiness();
  const rented = usePhoneLine(business.id).data?.rented_number;
  if (rented && rented.status === "active") {
    return (
      <p className="font-medium text-ink">
        {t("phoneNumbers.panel.disconnectReleases", { number: numberInText(rented.display_number) })}
      </p>
    );
  }
  return <p>{t("channels.disconnectPhoneNote")}</p>;
}
