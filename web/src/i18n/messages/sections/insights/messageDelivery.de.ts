/** `messageDelivery.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { messageDeliveryEn } from "./messageDelivery.en";

export const messageDeliveryDe: Translation<typeof messageDeliveryEn> = {
  label: "Zustellung",
  states: {
    sending: "Wird gesendet…",
    retrying: "Noch nicht zugestellt, neuer Versuch",
    delivered: "Zugestellt",
    failed: "Nicht zugestellt",
  },
  nextAttempt: "nächster Versuch um {time}",
  reasons: {
    rate_limited: "der Messenger hat um Warten gebeten",
    provider_unavailable: "der Messenger hat nicht geantwortet",
    recipient_refused: "der Messenger hat sie abgelehnt (der Kunde hat das Unternehmen vielleicht blockiert, oder das 24-Stunden-Fenster ist geschlossen)",
    template_rejected: "WhatsApp hat die Nachrichtenvorlage nicht akzeptiert",
    channel_disconnected: "der Kanal ist nicht mehr verbunden",
    credential_rejected: "der Zugang des Kanals funktioniert nicht mehr: Verbinden Sie ihn unter Kanäle neu",
    not_configured: "nichts kann diese Nachricht übermitteln",
    expired: "ihr Zeitpunkt ist verstrichen, bevor sie gesendet werden konnte",
  },
};
