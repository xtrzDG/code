/** `sources.*` texts: „საიდან მოვიდნენ კლიენტები“ ანგარიშებში და წყაროს ნიშანი შემოსულებში, ქართულად. */

import type { Translation } from "../../../translate";
import type { sourcesEn } from "./sources.en";

export const sourcesKa: Translation<typeof sourcesEn> = {
  title: "საიდან მოვიდნენ კლიენტები",
  description: "საუბრები, ჯავშნები და მათი ღირებულება — ყოველი ბმულის, QR კოდის, რეკლამისა და ტელეფონის ნომრის მიხედვით.",
  periodLabel: "პერიოდი",
  periods: {
    "7d": "7 დღე",
    "30d": "30 დღე",
    "90d": "90 დღე",
  },
  caption: "კლიენტები წყაროების მიხედვით, {range}",
  columns: {
    source: "წყარო",
    conversations: "საუბრები",
    bookings: "ჯავშნები",
    requests: "მოთხოვნები",
    value: "ღირებულება",
  },
  untagged: "ნიშნულის გარეშე",
  other: { one: "კიდევ {count} ნიშნული", other: "კიდევ {count} ნიშნული" },
  phone: "ზარი ნომერზე {number}",
  ad: "რეკლამა",
  adWithId: "რეკლამა {id}",
  total: "სულ",
  noValue: "—",
  share: "საუბრების {percent}",
  empty: {
    title: "ამ პერიოდში საუბრები არ ყოფილა",
    description: "წყაროები გამოჩნდება, როცა კლიენტები მოგწერენ ან დაგირეკავენ.",
  },
  tagHint: "მიეცით ყოველ ბმულს და QR კოდს საკუთარი ნიშნული „არხები“ → „გაზიარება“ — და აქ მათ ცალკე სტრიქონი ექნებათ.",
  tagLink: "ნიშნულების დასმა",
  loading: "წყაროები იტვირთება…",
};
