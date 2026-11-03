/**
 * The scripts the payment pages load, and what changed in them (PAY-02;
 * PCI DSS 11.6.1 intent, the script inventory of 6.4.3). The payment pages
 * are the billing page, which sends the payer to Flitt's or Stripe's page,
 * and the hosted chat page, which shows a deposit's payment link
 * (src/lib/paymentPages.ts). Every script they load is a first-party chunk
 * of the build under /_next/static/; payment-page-scripts.json lists each
 * with its SHA-384 (the reviewed inventory), and
 * payment-page-integrity.mjs compares the build or the deployed files with
 * it every week (.github/workflows/payment-page-integrity.yml).
 *
 * A page's scripts: the build's polyfills and main files, the entry files
 * of every segment of its route and the chunks of its client components
 * (the route's build manifests), and every chunk those name in turn (the
 * lazily loaded ones). Pure: the scripts that use it read and hash files.
 */

/** The App Router routes of the payment pages, as the build names them. */
export const PAYMENT_PAGES = ["/b/[businessId]/settings/billing", "/c/[slug]"];

const SCRIPT_PATH = /^static\/(?:[A-Za-z0-9._-]+\/)*[A-Za-z0-9._-]+\.js$/;
const CHUNK_REFERENCE = /static\/chunks\/[A-Za-z0-9._-]+\.js/g;
const INTEGRITY = /^sha384-[A-Za-z0-9+/]{64}$/;

/** The build manifests of a route, relative to the build directory. */
export function routeManifestPaths(route) {
  return {
    buildManifest: `server/app${route}/page/build-manifest.json`,
    clientManifest: `server/app${route}/page_client-reference-manifest.js`,
  };
}

/** The JSON object a `page_client-reference-manifest.js` assigns for the route's page. */
export function parseClientManifest(text, route) {
  const marker = `__RSC_MANIFEST[${JSON.stringify(`${route}/page`)}] = `;
  const start = text.indexOf(marker);
  const end = text.lastIndexOf("}");
  if (start < 0 || end < start) {
    throw new Error(`payment pages: no client manifest for ${route} (did the build's format change?)`);
  }
  return JSON.parse(text.slice(start + marker.length, end + 1));
}

/** The scripts a route's documents load first, from its two build manifests. */
export function entryScripts(buildManifest, clientManifest) {
  const files = [...(buildManifest.polyfillFiles ?? []), ...(buildManifest.rootMainFiles ?? [])];
  for (const list of Object.values(clientManifest.entryJSFiles ?? {})) {
    files.push(...list);
  }
  for (const clientModule of Object.values(clientManifest.clientModules ?? {})) {
    files.push(...(clientModule.chunks ?? []).map((chunk) => chunk.replace(/^\/_next\//, "")));
  }
  return [...new Set(files.filter((file) => SCRIPT_PATH.test(file)))].sort();
}

/** The entry scripts and every chunk they name, transitively: `read(path)` gives a script's text. */
export function loadedScripts(entries, read) {
  const seen = new Set();
  const pending = [...entries];
  while (pending.length > 0) {
    const path = pending.pop();
    if (seen.has(path)) {
      continue;
    }
    seen.add(path);
    for (const reference of read(path).match(CHUNK_REFERENCE) ?? []) {
      pending.push(reference);
    }
  }
  return [...seen].sort();
}

/** The committed inventory, checked: `{ pages: { route: [{ path, integrity }] } }` for exactly PAYMENT_PAGES. */
export function parseInventory(raw) {
  const pages = raw?.pages;
  if (typeof pages !== "object" || pages === null) {
    throw new Error("payment page scripts: `pages` is missing");
  }
  const routes = Object.keys(pages).sort();
  if (JSON.stringify(routes) !== JSON.stringify([...PAYMENT_PAGES].sort())) {
    throw new Error(`payment page scripts: the pages must be exactly ${PAYMENT_PAGES.join(", ")}`);
  }
  for (const [route, scripts] of Object.entries(pages)) {
    if (!Array.isArray(scripts) || scripts.length === 0) {
      throw new Error(`payment page scripts: ${route} lists no script`);
    }
    for (const script of scripts) {
      if (!SCRIPT_PATH.test(script?.path ?? "") || !INTEGRITY.test(script?.integrity ?? "")) {
        throw new Error(`payment page scripts: ${route} has an entry without a build path and a sha384 integrity`);
      }
    }
  }
  return { pages };
}

/**
 * What differs between the reviewed inventory and what was found, page by
 * page: a script `added`, `removed` or `changed`, or one the deployed site
 * did not serve (`unavailable`, with its HTTP status). Empty: nothing changed.
 */
export function differences(expected, found) {
  const changes = [];
  for (const route of PAYMENT_PAGES) {
    const before = new Map((expected.pages[route] ?? []).map((script) => [script.path, script]));
    const after = new Map((found.pages[route] ?? []).map((script) => [script.path, script]));
    for (const [path, script] of after) {
      const previous = before.get(path);
      if (script.status !== undefined) {
        changes.push({ route, path, kind: "unavailable", detail: `HTTP ${script.status}` });
      } else if (!previous) {
        changes.push({ route, path, kind: "added", detail: script.integrity });
      } else if (previous.integrity !== script.integrity) {
        changes.push({ route, path, kind: "changed", detail: `${previous.integrity} → ${script.integrity}` });
      }
    }
    for (const path of before.keys()) {
      if (!after.has(path)) {
        changes.push({ route, path, kind: "removed", detail: before.get(path).integrity });
      }
    }
  }
  return changes;
}

/** The run summary: what was compared and every difference. */
export function renderReport(changes, source) {
  const lines = ["## Payment page scripts", "", `Compared: ${source} against web/payment-page-scripts.json.`, ""];
  if (changes.length === 0) {
    lines.push("Every script of the payment pages is the reviewed one.");
    return `${lines.join("\n")}\n`;
  }
  lines.push(
    `**${changes.length} difference(s).** Only reviewed code explains them: in a pull request, review`,
    "the changed scripts and update the inventory in it; on the deployed site, a change no reviewed",
    'commit made is an incident (docs/operations/ci.md, "Payment page integrity"; docs/operations/incident.md).',
    "",
    "| Page | Script | Change | Detail |",
    "| --- | --- | --- | --- |",
    ...changes.map(({ route, path, kind, detail }) => `| \`${route}\` | \`${path}\` | ${kind} | ${detail} |`),
  );
  return `${lines.join("\n")}\n`;
}
