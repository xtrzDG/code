import { accessibilityStatementPath, customerPageLinkNames } from "@/lib/publicSite/customerPageLinks";

const LINK = "underline underline-offset-4 hover:no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus";

/**
 * The foot of a page customers see (the hosted chat, the booking page):
 * the business's privacy notice (when there is one to link) and the
 * platform's accessibility statement, named in the page's language.
 */
export function CustomerPageLinks({
  language,
  privacyHref,
  className,
}: {
  language: string;
  privacyHref: string | null;
  className?: string;
}) {
  const names = customerPageLinkNames(language);
  const statement = accessibilityStatementPath(language);
  const isExternal = privacyHref !== null && !privacyHref.startsWith("/");
  return (
    <footer className={className} data-testid="customer-page-links">
      <ul lang={names.language} className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
        {privacyHref ? (
          <li>
            <a href={privacyHref} className={LINK} {...(isExternal ? { target: "_blank", rel: "noopener noreferrer" } : {})}>
              {names.privacy}
            </a>
          </li>
        ) : null}
        <li>
          <a href={statement} hrefLang={statement.split("/")[1]} className={LINK}>
            {names.accessibility}
          </a>
        </li>
      </ul>
    </footer>
  );
}
