/** `accessibility.*`: the accessibility statement (/[locale]/accessibility), English. */

export const accessibilityEn = {
  nav: "Accessibility",
  description:
    "How accessible the platform's website, the businesses' chat and booking pages and the owners' cabinet are, what is not accessible yet, and how to report a barrier.",
  title: "Accessibility statement",
  lead: "{operator} wants everyone, including people with disabilities, to be able to use its service. This statement covers this website, the businesses' chat pages and website chat, the guests' booking pages and the owners' cabinet.",
  operatorFallback: "The provider of this service",
  basis:
    "It follows the model published by AgID (the Agency for Digital Italy) and the accessibility requirements of the European Accessibility Act (Directive (EU) 2019/882) and of the Italian Law 4/2004.",
  statusTitle: "Compliance status",
  statusText:
    "The service is partially compliant with the Web Content Accessibility Guidelines (WCAG) 2.2 at level AA, the level the European standard EN 301 549 refers to. Partially compliant means that some parts do not yet fully meet these requirements; the ones we know of are listed below.",
  limitationsTitle: "Content that is not yet accessible",
  limitations: {
    legalLanguage:
      "The legal texts (terms of service, privacy policy, cookie statement and data processing agreement) are published in English only; the Italian versions are being prepared. Until then, ask us through the contacts below and we explain any clause in Italian, in writing or by phone.",
    userContent:
      "Photos and files that businesses or their customers send in a conversation, and the texts businesses write themselves, may lack a text description or a clear structure: we cannot check everything they publish. Ask the business for the same information by phone or in a message, or ask us to pass on your request.",
    thirdParty:
      "Pages of other services the platform leads to are not covered by this statement: the bot check at sign-in (Cloudflare Turnstile), the payment pages (Flitt, Stripe) and the businesses' own websites. If the bot check stops you, write to us and we help you sign in; instead of an online payment you can ask the business for another way to pay.",
    audit:
      "No full manual audit with assistive technologies (such as screen readers) has been carried out yet, so barriers that automated checks cannot find may remain. Report any barrier you meet: we answer within 30 days and tell you how to get what you needed meanwhile.",
  },
  methodTitle: "How this statement was prepared",
  methodText:
    "It is based on a self-assessment by the provider, not on an audit by an independent expert. The axe-core tool automatically checks the public pages, the chat page, the website chat, the booking page and the cabinet's pages against its WCAG 2.0, 2.1 and 2.2 rules at levels A and AA (the public pages and the cabinet's in both the light and the dark theme). Automated tools find only part of the possible problems.",
  dateText: "This statement was prepared on {date} and is reviewed at least once a year and whenever the service changes significantly.",
  feedbackTitle: "Feedback and contact",
  feedbackText:
    "If you meet a barrier, or need something from the service in another format, tell us which page it was and what went wrong. We answer within 30 days.",
  feedbackEmail: "Write to {email}.",
  feedbackContact: "Use the contacts on the Contact page.",
  contactLink: "Contact",
  enforcementTitle: "Enforcement procedure",
  enforcementText:
    "If our answer is unsatisfactory, or you have had none within 30 days, you can report it to AgID (the Agency for Digital Italy), the authority that oversees digital accessibility in Italy, with its online form.",
  enforcementLink: "Report to AgID (form.agid.gov.it)",
  technologiesTitle: "Technologies",
  technologiesText:
    "The service relies on HTML, CSS, JavaScript and WAI-ARIA, and is meant for the current versions of Chrome, Edge, Firefox and Safari on computers and phones.",
} as const;
