import { PublicPageFrame } from "@/components/help/PublicPageFrame";

/** The platform's status page: public, signed in or not. */
export default function StatusLayout({ children }: LayoutProps<"/status">) {
  return <PublicPageFrame>{children}</PublicPageFrame>;
}
