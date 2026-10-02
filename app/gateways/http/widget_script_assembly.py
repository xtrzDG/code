"""The website chat widget script, assembled from its source parts.

`/widget.js` is served as one dependency-free script. Its source lives in
small parts under `static/widget/`, concatenated in the fixed order below:
the first part opens the script's closure and the last one closes it, and
`mount` (one closure over the chat panel) spans the four `mount_*` parts.
A part is a slice of that one script, so it need not parse on its own.
"""

from pathlib import Path

WIDGET_SCRIPT_PARTS_DIRECTORY_NAME: str = "widget"
WIDGET_SCRIPT_PART_FILE_NAMES: tuple[str, ...] = (
    # Licence comment, the closure, constants shared with the API.
    "header.js",
    # Interface texts (one `TEXTS` object): English and Latin-script Europe,
    "texts_latin_europe.js",
    # Cyrillic, Caucasian and Turkic languages,
    "texts_cyrillic_caucasus_turkic.js",
    # the Middle East and Asia.
    "texts_middle_east_asia.js",
    # The stylesheet of the shadow root.
    "styles.js",
    # Finding the own script tag, its business and the API, loading the config.
    "boot.js",
    # mount: the panel's elements, their events and the first poll,
    "mount_panel.js",
    # language, opening and closing, sending a message, receiving the reply,
    "mount_interaction.js",
    # polling for answers not shown yet and sharing state between tabs,
    "mount_polling.js",
    # failures, rate limits, rendering the log and saving the history.
    "mount_rendering.js",
    # Choosing the interface language, accent colour and corner; texts.
    "language.js",
    # JSON requests to the API and Retry-After.
    "transport.js",
    # The error beacon: errors of the widget's own code, without texts.
    "errors.js",
    # The visitor key and history in localStorage (never cookies).
    "storage.js",
    # DOM, SVG and colour helpers, console messages; closes the closure.
    "dom.js",
)


def assemble_widget_script(static_directory: Path) -> str:
    """The served script: every part, in order, without anything in between."""

    parts_directory: Path = static_directory / WIDGET_SCRIPT_PARTS_DIRECTORY_NAME
    return "".join(
        (parts_directory / part_file_name).read_text(encoding="utf-8")
        for part_file_name in WIDGET_SCRIPT_PART_FILE_NAMES
    )
