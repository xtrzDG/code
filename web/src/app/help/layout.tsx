import { PublicPageFrame } from "@/components/help/PublicPageFrame";

/** The help center: public, signed in or not. */
export default function HelpLayout({ children }: LayoutProps<"/help">) {
  return <PublicPageFrame>{children}</PublicPageFrame>;
}
