  // --- colours: the business's accent and the text on it ------------------

  // WCAG AA for the header's title, the launcher and the send button.
  var AA_CONTRAST = 4.5;
  var WHITE_TEXT = "#ffffff";
  // The ink of the dark scheme, the darker text on a light accent.
  var INK_TEXT = "#1a1816";
  // Each step keeps this much of the accent's channels (toward black).
  var DARKEN_STEP = 0.92;

  // The accent the widget paints and the text on it, readable whatever
  // colour the owner chose: white text, else ink text, else the owner's
  // colour darkened step by step until white text reaches AA on it.
  function accentColors(hexColor) {
    var channels = hexChannels(hexColor);
    if (contrastRatio(channels, hexChannels(WHITE_TEXT)) >= AA_CONTRAST) {
      return { accent: toHexColor(channels), onAccent: WHITE_TEXT };
    }
    if (contrastRatio(channels, hexChannels(INK_TEXT)) >= AA_CONTRAST) {
      return { accent: toHexColor(channels), onAccent: INK_TEXT };
    }
    var darker = channels;
    while (contrastRatio(darker, hexChannels(WHITE_TEXT)) < AA_CONTRAST) {
      darker = darker.map(function (channel) {
        return Math.floor(channel * DARKEN_STEP);
      });
    }
    return { accent: toHexColor(darker), onAccent: WHITE_TEXT };
  }

  function hexChannels(hexColor) {
    var hex = String(hexColor).replace(/^#/, "");
    if (hex.length === 3) {
      hex = hex.charAt(0) + hex.charAt(0) + hex.charAt(1) + hex.charAt(1) + hex.charAt(2) + hex.charAt(2);
    }
    return [0, 2, 4].map(function (offset) {
      return parseInt(hex.slice(offset, offset + 2), 16);
    });
  }

  function toHexColor(channels) {
    return (
      "#" +
      channels
        .map(function (channel) {
          var hex = channel.toString(16);
          return hex.length === 1 ? "0" + hex : hex;
        })
        .join("")
    );
  }

  // WCAG relative luminance and contrast ratio.
  function relativeLuminance(channels) {
    var linear = channels.map(function (channel) {
      var value = channel / 255;
      return value <= 0.03928 ? value / 12.92 : Math.pow((value + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  }

  function contrastRatio(first, second) {
    var lighter = Math.max(relativeLuminance(first), relativeLuminance(second));
    var darker = Math.min(relativeLuminance(first), relativeLuminance(second));
    return (lighter + 0.05) / (darker + 0.05);
  }

  // A theme the script tag asks for ("light" or "dark"), else the system's.
  function chooseTheme(attribute) {
    var theme = String(attribute || "").trim().toLowerCase();
    return THEMES.indexOf(theme) !== -1 ? theme : "";
  }

