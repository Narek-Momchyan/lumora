"""Safe SVG: an allowlist of drawing elements and attributes, everything else is dropped.

/media/ is served from the site's own origin, and an SVG opened directly is a document that can
run scripts. So an SVG we store (a club crest from football-data.org, a sidebar icon uploaded in
the admin) keeps only shapes, paints and gradients: no scripts, event handlers, foreignObject,
embedded images, animations, external links or CSS that loads URLs. defusedxml refuses DTDs and
entities, so XXE and "billion laughs" files fail to parse.
"""

import re
import xml.etree.ElementTree as ET

from defusedxml import ElementTree as SafeET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
MAX_SVG_BYTES = 1024 * 1024

ELEMENTS = {
    "svg", "g", "defs", "title", "desc", "path", "rect", "circle", "ellipse", "line", "polyline",
    "polygon", "linearGradient", "radialGradient", "stop", "clipPath", "mask", "use", "symbol",
    "text", "tspan", "pattern",
}  # fmt: skip

ATTRIBUTES = {
    "id", "class", "d", "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry", "fx", "fy",
    "width", "height", "viewBox", "preserveAspectRatio", "version", "points", "transform",
    "fill", "fill-rule", "fill-opacity", "stroke", "stroke-width", "stroke-linecap",
    "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
    "stroke-opacity", "opacity", "clip-path", "clip-rule", "clipPathUnits", "mask", "maskUnits",
    "maskContentUnits", "offset", "stop-color", "stop-opacity", "gradientUnits",
    "gradientTransform", "spreadMethod", "patternUnits", "patternContentUnits", "patternTransform",
    "display", "visibility", "style", "font-family", "font-size", "font-weight", "font-style",
    "text-anchor", "letter-spacing", "dominant-baseline", "href",
}  # fmt: skip

# A value may point only inside the same file: url(#id) or #id.
EXTERNAL_URL = re.compile(r"url\(\s*['\"]?\s*(?!#)", re.IGNORECASE)
DANGEROUS_VALUE = re.compile(r"javascript:|data:|expression\(|@import|<", re.IGNORECASE)


class UnsafeSvg(ValueError):
    pass


def local_name(name):
    return name.rsplit("}", 1)[-1]


def namespace(name):
    return name[1:].split("}", 1)[0] if name.startswith("{") else ""


def safe_attribute(name, value):
    ns = namespace(name)
    local = local_name(name)
    if ns not in ("", XLINK_NS) or local not in ATTRIBUTES:
        return False
    if local == "href":
        return value.strip().startswith("#")
    return not EXTERNAL_URL.search(value) and not DANGEROUS_VALUE.search(value)


def copy_clean(element):
    clean = ET.Element(f"{{{SVG_NS}}}{local_name(element.tag)}")
    for name, value in element.attrib.items():
        if safe_attribute(name, value):
            key = f"{{{XLINK_NS}}}href" if namespace(name) == XLINK_NS else local_name(name)
            clean.set(key, value)
    clean.text = element.text if local_name(element.tag) in ("text", "tspan", "title", "desc") else None
    for child in element:
        if namespace(child.tag) in ("", SVG_NS) and local_name(child.tag) in ELEMENTS:
            clean.append(copy_clean(child))
            clean[-1].tail = None
    return clean


def sanitize_svg(data: bytes) -> bytes:
    """The SVG with only the allowed parts. Raises UnsafeSvg if it isn't a parseable <svg>."""
    if len(data) > MAX_SVG_BYTES:
        raise UnsafeSvg("SVG is larger than 1 MB.")
    try:
        root = SafeET.fromstring(data, forbid_dtd=True)
    except Exception as exc:  # defusedxml raises its own errors for DTDs and entities
        raise UnsafeSvg(f"Not a valid SVG: {exc}") from exc
    if namespace(root.tag) not in ("", SVG_NS) or local_name(root.tag) != "svg":
        raise UnsafeSvg("The file's root is not <svg>.")

    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    return ET.tostring(copy_clean(root), encoding="utf-8", xml_declaration=False)


def is_safe_svg(data: bytes) -> bool:
    """True when sanitising removes nothing (an admin upload must already be clean)."""
    try:
        original = SafeET.fromstring(data, forbid_dtd=True)
        clean = SafeET.fromstring(sanitize_svg(data))
    except Exception:
        return False
    return size(original) == size(clean)


def size(root):
    # Elements and attributes; xmlns declarations aren't attributes in ElementTree.
    return sum(1 + len(element.attrib) for element in root.iter())
