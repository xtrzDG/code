/**
 * Messenger brands, drawn in the same outline style (not the official marks).
 * The path data lives in `@/lib/channelMarks`, shared with the landing's 3D
 * scene, which draws the same marks on its message bubbles.
 */

import { CHANNEL_MARKS } from "@/lib/channelMarks";
import type { ChannelMarkKey } from "@/lib/heroScene";

import { Icon, type IconProps } from "./Icon";

function MarkPaths({ mark }: { mark: ChannelMarkKey }) {
  return CHANNEL_MARKS[mark].paths.map((path) => <path key={path} d={path} />);
}

export const IconWhatsApp = (props: IconProps) => (
  <Icon {...props}>
    <MarkPaths mark="whatsapp" />
  </Icon>
);

export const IconInstagram = (props: IconProps) => (
  <Icon {...props}>
    <MarkPaths mark="instagram" />
  </Icon>
);

export const IconMessenger = (props: IconProps) => (
  <Icon {...props}>
    <MarkPaths mark="messenger" />
  </Icon>
);

export const IconTelegram = (props: IconProps) => (
  <Icon {...props}>
    <MarkPaths mark="telegram" />
  </Icon>
);

/** The mark of any customer channel, by its key (`phone`, `web_chat` included). */
export const IconChannelMark = ({ mark, ...props }: IconProps & { mark: ChannelMarkKey }) => (
  <Icon {...props}>
    <MarkPaths mark={mark} />
  </Icon>
);
