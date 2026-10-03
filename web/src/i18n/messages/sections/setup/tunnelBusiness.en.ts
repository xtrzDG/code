/**
 * `tunnelBusiness.*`: the first two screens of "Create an AI assistant":
 * what the business is (name, kind, the one or two things customers of
 * that kind always ask) and where it is (country, city, address,
 * languages). English is the reference.
 */

export const tunnelBusinessEn = {
  business: {
    title: "What's your business called?",
    text: "We'll create an assistant that answers your customers for you, day and night.",
    name: "Business name",
    namePlaceholder: "For example, Salon Morgenrot",
    kindTitle: "What do you do?",
    kindHint: "Pick the closest one. It decides what your assistant asks, books and knows.",
    kindFixed: "You chose this when the assistant was created; it can't be changed.",
    kindLoadFailed: "We couldn't load the kinds of business.",
    legalReview: "Businesses of this kind get a short legal check before the assistant goes live.",
    detailsTitle: "One more thing customers always ask",
    errors: {
      name: "Write the name of your business.",
      kind: "Choose what your business does.",
    },
  },
  place: {
    title: "Where are you?",
    text: "Your country sets the currency, the time zone and your customers' languages. We've filled in what we could.",
    country: "Country",
    countryHint: "Prices in {currency}",
    countryFixed: "The country can't be changed once the assistant exists.",
    city: "City",
    cityPlaceholder: "For example, Tbilisi",
    address: "Address",
    addressPlaceholder: "Street and number",
    addressHint: "The assistant tells customers how to find you.",
    addressOptional: "optional",
    languages: "Languages your customers write in",
    languagesHint: "The assistant answers each customer in their language, among these.",
    defaultLanguage: "First greeting in",
    timezone: "Time zone",
    loadFailed: "We couldn't load the countries.",
    creating: "Creating your assistant…",
    errors: {
      country: "Choose your country.",
      languages: "Choose at least one language.",
      address: "Write your address: customers need it to find you.",
      restricted: "Businesses from this country can't be created yet.",
    },
  },
} as const;
