/** `adminSpend.*` texts of the platform admin's "Spend today" tile, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminSpendEn } from "./adminSpend.en";

export const adminSpendIt: Translation<typeof adminSpendEn> = {
  title: "Spesa di oggi",
  description: "Quanto la piattaforma deve ai suoi fornitori per il {day} (UTC). I costi che un fornitore non ha ancora comunicato sono calcolati ai prezzi previsti.",
  total: "Totale di oggi",
  weekMean: "Media giornaliera dei 7 giorni precedenti: {amount}",
  spike: "Molto sopra il solito",
  budget: "{percent}% del budget giornaliero di {amount}",
  budgetLabel: "Budget giornaliero usato",
  noBudget: "Nessun budget giornaliero impostato (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "Spesa per fornitore",
  providers: {
    language_model: "Modello AI",
    voice: "Assistente vocale",
    telephony: "Chiamate",
    whatsapp: "Modelli WhatsApp",
    transcription: "Trascrizione dei messaggi vocali",
  },
  brakedTitle: "Clienti oltre un limite di spesa",
  brakedNone: "Oggi nessun cliente ha superato un limite di spesa.",
  levels: {
    soft_limit: "Modello più economico",
    hard_limit: "Solo richieste",
  },
  brakedLine: "{spend} di {limit}, dalle {time}",
};
