/** `adminActions.*` texts of the admin client page's account actions, in Italian (draft awaiting a native speaker's review). */

import type { Translation } from "../../../translate";
import type { adminActionsEn } from "./adminActions.en";

export const adminActionsIt: Translation<typeof adminActionsEn> = {
  menu: "Azioni sull'account",
  reasonLabel: "Motivo",
  reasonHint: "Resta nel registro di audit del cliente, con il tuo nome.",
  reasonShort: "Indica il motivo in almeno 8 caratteri.",
  done: "Salvato nell'account del cliente",
  autoDebitNote:
    "Questo cliente paga in automatico: alla carta continua a essere addebitato l'importo concordato al checkout. Sconti e credito valgono per le fatture pagate nel pannello o con bonifico.",
  extend: {
    action: "Prolunga la prova gratuita",
    title: "Prolunga la prova gratuita di {name}",
    description:
      "Una prova in corso finisce più tardi; una prova terminata senza pagamento riparte da oggi, le sue fatture vengono annullate e il servizio completo torna attivo.",
    days: "Giorni in più",
    daysHint: "Da 1 a 60 giorni.",
    daysInvalid: "Inserisci un numero intero di giorni da 1 a 60.",
    confirm: "Prolunga",
  },
  discount: {
    action: "Applica uno sconto",
    title: "Uno sconto per {name}",
    description:
      "I periodi che iniziano entro l'ultimo giorno vengono fatturati con questo sconto sul prezzo, al netto delle imposte. Un nuovo sconto sostituisce quello attuale.",
    percent: "Sconto, %",
    percentInvalid: "Inserisci una percentuale intera da 1 a 100.",
    lastDay: "Ultimo giorno",
    lastDayHint: "Nel fuso orario del cliente; al massimo tre anni da oggi.",
    lastDayInvalid: "Scegli un giorno da oggi in poi.",
    confirm: "Applica lo sconto",
  },
  credit: {
    action: "Concedi un credito",
    title: "Credito per {name}",
    description:
      "Il credito viene scalato dal prezzo delle prossime fatture, al netto delle imposte, finché non si esaurisce. Una fattura annullata restituisce il suo credito.",
    amount: "Importo, {currency}",
    amountInvalid: "Inserisci un importo maggiore di zero (al massimo due decimali).",
    confirm: "Concedi il credito",
  },
  waive: {
    action: "Abbuona il costo di configurazione",
    title: "Abbuonare il costo di configurazione di {name}?",
    description:
      "La fattura non pagata del costo di configurazione viene annullata e il costo non viene più fatturato. Un costo già pagato si rimborsa tramite il fornitore dei pagamenti, non qui.",
    confirm: "Abbuona il costo",
  },
  payment: {
    action: "Registra un pagamento",
    title: "Registra un pagamento di {name}",
    description:
      "Il denaro arrivato al di fuori del pagamento con carta salda subito una fattura aperta. Un periodo pagato riattiva il servizio completo, come farebbe un pagamento con carta.",
    invoice: "Fattura",
    noOpenInvoices: "Il cliente non ha fatture aperte.",
    method: "Come è arrivato",
    methods: {
      bank_transfer: "Bonifico bancario",
      cash: "Contanti",
    },
    reference: "Riferimento",
    referenceHint: "La causale dell'estratto conto o il numero della ricevuta in contanti.",
    referenceInvalid: "Inserisci il riferimento (fino a 120 caratteri).",
    confirm: "Segna come pagata",
  },
  plan: {
    action: "Cambia il piano",
    title: "Cambia il piano di {name}",
    description:
      "La prossima fattura usa il prezzo del listino, senza checkout. Se l'importo addebitato cambia, i pagamenti automatici si fermano e le fatture non pagate al vecchio prezzo vengono annullate; un piano senza voce disattiva l'assistente vocale.",
    plan: "Piano",
    period: "Fatturazione",
    confirm: "Cambia il piano",
  },
  account: {
    title: "Concesso al cliente",
    description: "Cosa il team della piattaforma ha dato a questo account: la prova gratuita, uno sconto, un credito e il costo di configurazione.",
    trialEnds: "Fine della prova gratuita",
    noTrial: "Nessuna prova in corso",
    discount: "Sconto",
    discountActive: "{percent} sui periodi che iniziano fino al {date}",
    discountEnded: "{percent}, terminato il {date}",
    noDiscount: "Nessuno",
    credit: "Credito residuo",
    setupFee: "Costo di configurazione",
    setupFeeWaived: "Abbuonato",
    setupFeeCharged: "Addebitato quando previsto",
    noSubscription: "Il cliente non ha ancora un abbonamento: le azioni sull'account ne richiedono uno.",
  },
  onboarding: {
    title: "Configurazione assistita richiesta",
    description: "Il {date} il titolare ha chiesto al team della piattaforma di configurare l'attività ({plan}).",
    markDone: "Segna come completata",
    marked: "La configurazione assistita è segnata come completata",
  },
};
