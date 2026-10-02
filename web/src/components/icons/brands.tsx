/** Messenger brands, drawn in the same outline style (not the official marks). */

import { Icon, type IconProps } from "./Icon";

export const IconWhatsApp = (props: IconProps) => (
  <Icon {...props}>
    <path d="M4 20l1.3-4A8.5 8.5 0 1112 20.5a8.4 8.4 0 01-4-1z" />
    <path d="M9 8.5c0 3.2 2.3 6 5.5 6.5l1-1.5-1.8-1-1 .8a4.5 4.5 0 01-2.5-2.5l.8-1-1-1.8z" />
  </Icon>
);

export const IconInstagram = (props: IconProps) => (
  <Icon {...props}>
    <rect x="3.5" y="3.5" width="17" height="17" rx="5" />
    <circle cx="12" cy="12" r="3.8" />
    <path d="M17 7h.01" />
  </Icon>
);

export const IconMessenger = (props: IconProps) => (
  <Icon {...props}>
    <path d="M12 3.5c-4.8 0-8.5 3.5-8.5 8 0 2.5 1.1 4.6 3 6v3l2.8-1.5c.9.3 1.8.4 2.7.4 4.8 0 8.5-3.5 8.5-8s-3.7-7.9-8.5-7.9z" />
    <path d="M7.5 13.5l3-3 2.5 2 3.5-3" />
  </Icon>
);
