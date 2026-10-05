/**
 * `adminSpend.*` texts: the platform admin's "Spend today" tile on the
 * clients overview (provider spend of the UTC day, the week's mean, the
 * daily budget, clients past a spend limit), in English: the reference
 * that ru and ka are typed against.
 */

export const adminSpendEn = {
  title: "Spend today",
  description: "What the platform owes its providers for {day} (UTC). Costs a provider has not reported yet are counted at planned prices.",
  total: "Total today",
  weekMean: "Daily mean of the 7 days before: {amount}",
  spike: "Far above usual",
  budget: "{percent}% of the daily budget of {amount}",
  budgetLabel: "Daily budget used",
  noBudget: "No daily budget is set (PLATFORM_DAILY_SPEND_BUDGET_USD).",
  providersLabel: "Spend by provider",
  providers: {
    language_model: "AI model",
    voice: "Voice agent",
    telephony: "Phone calls",
    whatsapp: "WhatsApp templates",
    transcription: "Voice note transcription",
  },
  brakedTitle: "Clients past a spend limit",
  brakedNone: "No client passed a spend limit today.",
  levels: {
    soft_limit: "Cheaper model",
    hard_limit: "Requests only",
  },
  brakedLine: "{spend} of {limit}, since {time}",
} as const;
