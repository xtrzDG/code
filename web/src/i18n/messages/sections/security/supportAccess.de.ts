/** `supportAccess.*` in German: platform support in a cabinet (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { supportAccessEn } from "./supportAccess.en";

export const supportAccessDe: Translation<typeof supportAccessEn> = {
  label: "Zugriff des Plattform-Supports",
  owner: {
    title: "Der Plattform-Support sieht sich Ihr Dashboard an",
    who: "{name}: „{reason}“",
    reason: "Grund: „{reason}“",
    until: "bis {time}",
    readOnly: "Der Support kann nur ansehen; ohne Sie lässt sich nichts ändern.",
    end: "Zugriff beenden",
    endTitle: "Zugriff des Plattform-Supports beenden?",
    endDescription: "Der Support verlässt Ihr Dashboard sofort, und auch seine Erlaubnis, etwas zu ändern, endet.",
    ended: "Der Plattform-Support hat keinen Zugriff mehr",
    allow: "Dem Support Änderungen erlauben",
    allowHint: "Zum Beispiel, wenn Sie ihn gebeten haben, den Assistenten für Sie einzurichten. Endet von selbst.",
    allowedUntil: "Der Support darf bis {time} Änderungen vornehmen",
    hours: "Wie lange",
    hourOptions: {
      one: "{count} Stunde",
      other: "{count} Stunden",
    },
    dayOption: "Einen Tag",
    weekOption: "Eine Woche",
    allowed: "Der Support darf Änderungen vornehmen",
    stopped: "Der Support kann wieder nur ansehen",
    staff: "Nur ein Inhaber kann den Zugriff beenden oder dem Support Änderungen erlauben.",
  },
  support: {
    title: "Sie sehen {name} als Plattform-Support",
    readOnly: "Nur lesen: Änderungen werden abgelehnt.",
    canWrite: "Vom Inhaber erlaubte Änderungen bis {time}",
    until: "Der Zugriff endet um {time}",
    leave: "Dashboard verlassen",
    left: "Sie haben das Dashboard verlassen",
  },
};
