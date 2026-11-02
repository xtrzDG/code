"""Run parts of the widget script in node, over a small recording DOM."""

import json
import re
import shutil
import subprocess

from tests.channels.widget_script_source import SCRIPT_SOURCE

# Elements and text nodes as plain objects: what a part builds can be read
# back, and markup in a text can never become elements (there is no parser).
RECORDING_DOM: str = """
function makeNode(kind, extra) {
  var node = Object.assign({ kind: kind, children: [], attributes: {} }, extra);
  node.appendChild = function (child) { node.children.push(child); return child; };
  node.setAttribute = function (name, value) { node.attributes[name] = String(value); };
  return node;
}
var document = {
  createElement: function (tagName) { return makeNode("element", { tagName: tagName }); },
  createTextNode: function (text) { return makeNode("text", { textContent: text }); }
};
function describe(node) {
  if (node.kind === "text") { return { text: node.textContent }; }
  var described = { tag: node.tagName, children: node.children.map(describe) };
  ["className", "href", "target", "rel", "textContent"].forEach(function (name) {
    if (node[name] !== undefined) { described[name] = node[name]; }
  });
  if (Object.keys(node.attributes).length) { described.attributes = node.attributes; }
  return described;
}
"""


def extract_function(name: str) -> str:
    """A function of the script, up to the brace at its own indentation."""

    match = re.search(rf"\n( +)function {name}\(.*?\n\1\}}\n", SCRIPT_SOURCE, re.S)
    assert match is not None, name
    return match.group(0)


def extract_variable(name: str) -> str:
    """A `var` of the script, one statement up to its semicolon."""

    match = re.search(rf"\n *var {name} = .*?;\n", SCRIPT_SOURCE, re.S)
    assert match is not None, name
    return match.group(0)


def run_in_node(program: str) -> object:
    """Run `program` (which prints one JSON value) and return that value."""

    node = shutil.which("node")
    assert node is not None
    result = subprocess.run(
        [node, "-e", RECORDING_DOM + program],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    parsed: object = json.loads(result.stdout)
    return parsed
