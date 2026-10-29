/** `roi.*` texts of the landing page's value calculator, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { roiEn } from "./roi.en";

export const roiIt: Translation<typeof roiEn> = {
  title: "Quanto ti costano le richieste perse?",
  subtitle: "Conta solo quelle che arrivano quando nessuno può rispondere. Il resto è semplice aritmetica, con i tuoi numeri.",
  niche: "Il tuo settore",
  missed: "Chiamate e messaggi persi o a cui rispondi troppo tardi, al mese",
  missedHint: "Una chiamata a cui nessuno ha risposto, un messaggio con risposta ore dopo",
  afterHours: "Di questi, fuori dall'orario di lavoro",
  check: "Scontrino medio",
  checkHint: "Uno scontrino tipico per questo settore; cambialo con il tuo",
  checkUnknown: "Qui lo scontrino varia molto: inserisci il tuo",
  conversion: "Richieste che diventano una prenotazione",
  plan: "Confronta con il piano",
  percent: "{value}%",
  resultLabel: "L'assistente porterebbe circa",
  bookings: {
    one: "{count} prenotazione in più al mese",
    other: "{count} prenotazioni in più al mese",
  },
  bookingsUnderOne: "meno di una prenotazione in più al mese",
  perMonth: "{value} al mese",
  multiple: "{multiple}× il prezzo di {plan} ({price} al mese)",
  belowPrice: "Meno del prezzo di {plan} ({price} al mese): considera anche il tempo che il tuo team risparmia nel rispondere.",
  breakEven: {
    one: "{count} prenotazione al mese ripaga il piano",
    other: "{count} prenotazioni al mese ripagano il piano",
  },
  noCheck: "Inserisci uno scontrino medio per vedere l'importo.",
  breakdown: {
    label: "Come si arriva al totale",
    answered: "Risposte fuori dall'orario di lavoro",
    bookings: "Prenotazioni tra queste",
    check: "Scontrino medio",
  },
  note: "Una stima basata sui tuoi numeri, non una promessa. Nel pannello vedi i dati reali: richieste a cui è stata data risposta, prenotazioni e quanto hanno reso.",
  currency: "in {currency}",
};
