/**
 * `legalConsent.*` texts: the line on the sign-in page's code step that
 * says continuing accepts the terms, and the dialog that shows the terms,
 * the privacy policy and the cookie statement, in English: the reference
 * that ru and ka are typed against. `{terms}` and `{privacy}` become links.
 */

export const legalConsentEn = {
  line: "By continuing, you accept the {terms} and confirm you have read the {privacy}.",
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  cookies: "Cookie Statement",
  documentVersion: "Version of {date}",
  documentUpcoming: "From {date}, a new version applies.",
  otherLanguage: "This text is not translated into your language yet; it is shown in {language}.",
  template: "This text is still being completed: the fields in square brackets will be filled in before launch.",
  loading: "Loading the text…",
} as const;
