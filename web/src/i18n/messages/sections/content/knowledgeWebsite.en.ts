/**
 * `knowledge.*` texts of the import from the business's website, in English:
 * the reference that ru and ka are typed against.
 */

export const knowledgeWebsiteEn = {
  website: {
    tabsLabel: "What to import",
    tabMenu: "Menu or price list",
    tabWebsite: "From your website",
    title: "Import from your website",
    description:
      "Give the address of your site. We read up to 15 of its pages — menu, prices, services, questions and opening hours — and show you what we found before anything changes.",
    address: "Website address",
    addressHint: "Your own site, for example https://my-cafe.ge",
    start: "Read my website",
    starting: "Starting…",
    safety: "Only public pages are read. Nothing reaches customers until you check the items and add them.",
    progressLabel: "Reading your website",
    queued: "Starting in a moment…",
    opening: "Opening {host}…",
    reading: "Reading page {current} of {total}",
    found: { one: "{count} item found so far", other: "{count} items found so far" },
    leaveHint: "You can leave this page: the import keeps running and what it finds waits for you here.",
    doneTitle: { one: "Found {count} item on your website", other: "Found {count} items on your website" },
    doneDescription: {
      one: "{count} page read. Check the items before they are added.",
      other: "{count} pages read. Check the items before they are added.",
    },
    review: "Check what was found",
    waitingTitle: "Items from your website wait for you",
    waitingDescription: { one: "{count} item found on {host}.", other: "{count} items found on {host}." },
    nothingTitle: "Nothing to import was found",
    nothingDescription:
      "The pages had no menu, prices, services, questions or opening hours we could read. Try another address or add the items by hand.",
    another: "Try another address",
    sourcePage: "From {page}",
    errors: {
      required: "Enter your website address",
      address: "Enter a web address such as https://my-cafe.ge",
      failedTitle: "The website could not be read",
      notPublic: "This is not a public website. Use the address customers open in their browser.",
      notHttp: "Use a web address that starts with http:// or https://.",
      port: "Addresses with a port such as :8080 cannot be read. Use the usual address of your site.",
      credentials: "Remove the user name and password from the address.",
      unknownHost: "No website was found at this address. Check the spelling.",
      timeout: "The website took too long to answer. Try again in a few minutes.",
      unreachable: "The website could not be opened. Check the address and that the site is online.",
      httpStatus: "The website answered with error {status}. Check the address.",
      unreadable: "The address opened, but not as a web page we can read (a file, or too large). Try the address of your home page.",
      reader: "The reading service is not available right now. Try again later.",
      interrupted: "The import stopped before it finished. Start it again.",
      running: "Your website is already being read. Wait until that import finishes.",
      tooMany: "Your website was imported 10 times in the last hour. Try again later.",
    },
  },
} as const;
