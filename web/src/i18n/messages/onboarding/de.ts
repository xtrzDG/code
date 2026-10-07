import type { Translation } from "../../translate";
import type { onboardingEn } from "./en";
import { profileEditDe } from "./profileEdit.de";

/** Texts of the business profile in German (a draft awaiting native review). Keys as in en.ts. */
export const onboardingDe: Translation<typeof onboardingEn> = {
  onboarding: {
    choose: "Auswählen…",
    gaps: {
      times: { one: "{count}-mal", other: "{count}-mal" },
      notReady: { one: "{count} Pflichtangabe fehlt", other: "{count} Pflichtangaben fehlen" },
    },
    week: {
      closed: "Geschlossen",
      opens: "Öffnet",
      closes: "Schließt",
      addInterval: "Pause oder zweite Schicht hinzufügen",
      removeInterval: "Zeitraum entfernen",
      overnight: "bis {time} am nächsten Tag",
      roundTheClock: "24 Stunden geöffnet",
      copyToAll: "Montag auf alle Tage kopieren",
    },
    offer: {
      kinds: {
        faq: "Frage und Antwort",
        policy: "Regel",
        menu_item: "Gericht",
        service: "Leistung",
        room_type: "Zimmertyp",
        package: "Paket",
        vehicle: "Fahrzeug",
        product: "Produkt",
      },
    },
    booking: {
      noBookings: "Ihre Branche nimmt keine Buchungen an: Der Assistent sammelt Anfragen und gibt sie an den Manager weiter.",
      resourceKinds: {
        table: "Tisch",
        room: "Zimmer",
        staff: "Fachkraft",
        arena: "Platz oder Halle",
        bay: "Werkstattplatz",
        vehicle: "Fahrzeug",
        slot: "Zeitfenster",
      },
    },
    resources: {
      namePlaceholder: "Zum Beispiel: Platz 1",
    },
  },
  profileEdit: profileEditDe,
};
