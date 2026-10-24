/** Help and support icons: the "?" beside a page's title, e-mail, announcements. */

import { Icon, type IconProps } from "./Icon";

export const IconHelp = (props: IconProps) => (
  <Icon {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.6 9.3a2.5 2.5 0 0 1 4.85.85c0 1.65-2.45 2.2-2.45 3.6" />
    <path d="M12 17h.01" strokeWidth={2.25} />
  </Icon>
);

export const IconMail = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3" y="5" width="18" height="14" rx="2.5" />
    <path d="M4 7.5l8 5.5 8-5.5" />
  </Icon>
);

export const IconMegaphone = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 10v4a1 1 0 0 0 1 1h2l8 4V5L7 9H5a1 1 0 0 0-1 1z" />
    <path d="M7 15l1.5 4.5h2.5L9.8 15.9" />
    <path d="M18.5 9.5a3.5 3.5 0 0 1 0 5" />
  </Icon>
);
