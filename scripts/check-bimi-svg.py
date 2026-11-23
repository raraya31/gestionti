#!/usr/bin/env python3
"""Check a BIMI SVG Tiny PS logo against the rules for this repo.

The profile is draft-svg-tiny-ps-abrotman (SVG Tiny Portable/Secure) plus the
BIMI Group authoring rules: square viewBox, solid background, no root x/y,
no script, animation, raster image, or external reference, and under 32 KB.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = "http://www.w3.org/2000/svg"
SVG = f"{{{NS}}}"
MAX_BYTES = 32 * 1024

DISALLOWED = {
    "image",
    "script",
    "foreignObject",
    "switch",
    "audio",
    "video",
    "animation",
    "iframe",
    "canvas",
    "object",
    "embed",
    "handler",
    "listener",
    "discard",
    "a",
    "set",
    "animate",
    "animateColor",
    "animateMotion",
    "animateTransform",
    "mpath",
    "font",
    "font-face",
    "glyph",
}

ALLOWED = {
    "svg",
    "title",
    "desc",
    "defs",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
}


def local(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "assets/brand/2026-10/bimi.svg")
    data = path.read_bytes()
    text = data.decode("utf-8")
    errors: list[str] = []
    notes: list[str] = []

    print(f"file: {path}")
    print(f"bytes: {len(data)} (limit {MAX_BYTES})")
    if len(data) > MAX_BYTES:
        fail(errors, f"file is {len(data)} bytes, over the 32 KB limit")
    if b"\0" in data:
        fail(errors, "file contains a NUL byte")
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        fail(errors, "DOCTYPE or ENTITY is not allowed")
    # The SVG namespace is required on the root. Anything else that looks like
    # a URL, a data URI, or an xlink reference is an external resource.
    without_namespace = lowered.replace("http://www.w3.org/2000/svg", "")
    for needle in ("http://", "https://", "data:", "xlink:href"):
        if needle in without_namespace:
            fail(errors, f"found external reference marker {needle!r}")

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        fail(errors, f"XML parse error: {exc}")
        report(errors, notes)
        return 1

    if root.tag != f"{SVG}svg":
        fail(errors, f"root element is {root.tag}, expected svg in the SVG namespace")
    attrs = root.attrib
    if attrs.get("version") != "1.2":
        fail(errors, f"version is {attrs.get('version')!r}, expected '1.2'")
    if attrs.get("baseProfile") != "tiny-ps":
        fail(errors, f"baseProfile is {attrs.get('baseProfile')!r}, expected 'tiny-ps'")
    if "xmlns" in attrs and attrs["xmlns"] != NS:
        fail(errors, f"xmlns is {attrs.get('xmlns')!r}")
    elif not str(root.tag).startswith(f"{{{NS}}}"):
        fail(errors, "root is not in the SVG namespace")
    if "x" in attrs or "y" in attrs:
        fail(errors, "root svg must not set x or y")
    for key in attrs:
        if key.startswith("{http://www.w3.org/1999/xlink}") or key == "xlink:href":
            fail(errors, "root carries an xlink attribute")

    view_box = attrs.get("viewBox")
    if not view_box:
        fail(errors, "viewBox is missing")
    else:
        parts = view_box.replace(",", " ").split()
        if len(parts) != 4:
            fail(errors, f"viewBox {view_box!r} is not four numbers")
        else:
            try:
                min_x, min_y, width, height = (float(p) for p in parts)
            except ValueError:
                fail(errors, f"viewBox {view_box!r} is not numeric")
            else:
                if width != height or width <= 0:
                    fail(errors, f"viewBox is not a positive square ({width} x {height})")
                else:
                    notes.append(f"viewBox {view_box} is square")
                if min_x != 0 or min_y != 0:
                    notes.append(f"viewBox origin is {min_x},{min_y}")

    for dimension in ("width", "height"):
        if dimension in attrs and not attrs[dimension].replace(".", "", 1).isdigit():
            fail(errors, f"root {dimension}={attrs[dimension]!r} should be a unitless number")
    if "width" in attrs and "height" in attrs and attrs["width"] != attrs["height"]:
        fail(errors, "root width and height differ, so the image is not square")

    children = list(root)
    if not children:
        fail(errors, "svg has no children")
    else:
        first = children[0]
        if local(first.tag) != "title":
            fail(errors, f"first child is <{local(first.tag)}>, expected <title>")
        title = "".join(first.itertext()).strip()
        if not title:
            fail(errors, "title is empty")
        elif len(title) > 64:
            fail(errors, f"title is {len(title)} characters; the draft says it SHOULD be 64 or fewer")
        else:
            notes.append(f"title {title!r} ({len(title)} characters) is the first child")
        titles = [el for el in children if local(el.tag) == "title"]
        if len(titles) != 1:
            fail(errors, f"expected exactly one title element, found {len(titles)}")

    fills: set[str] = set()
    background = False
    vb_parts = view_box.split() if view_box else []
    vb_width = vb_parts[2] if len(vb_parts) == 4 else None
    vb_height = vb_parts[3] if len(vb_parts) == 4 else None

    def walk(el: ET.Element) -> None:
        nonlocal background
        name = local(el.tag)
        if name not in ALLOWED:
            fail(errors, f"element <{name}> is not in the allowed path/shape set")
        if name in DISALLOWED:
            fail(errors, f"disallowed element <{name}>")
        for key, value in el.attrib.items():
            attr = local(key)
            if attr in {"href", "xlink:href"} or key.endswith("}href"):
                fail(errors, f"<{name}> has {attr}={value!r}")
            if "://" in value or value.strip().lower().startswith("data:"):
                fail(errors, f"<{name} {attr}> points outside the file ({value!r})")
            if name == "svg" and attr in {"x", "y"}:
                fail(errors, "root svg must not set x or y")
        fill = el.attrib.get("fill")
        if fill:
            fills.add(fill.lower())
        if (
            name == "rect"
            and el.attrib.get("width") in {attrs.get("width"), vb_width}
            and el.attrib.get("height") in {attrs.get("height"), vb_height}
            and "x" not in el.attrib
            and "y" not in el.attrib
            and fill
            and fill.lower() not in {"none", "transparent"}
        ):
            background = True
        for child in list(el):
            walk(child)

    for child in children:
        walk(child)

    if not background:
        fail(errors, "no solid background rect covering the viewBox")
    else:
        notes.append("solid background rect covers the viewBox")
    if len(fills) < 2:
        fail(errors, f"rendered fills are {sorted(fills)}; Tiny PS expects at least two colours")
    else:
        notes.append(f"fills: {', '.join(sorted(fills))}")

    report(errors, notes)
    return 1 if errors else 0


def report(errors: list[str], notes: list[str]) -> None:
    print("notes:")
    for note in notes:
        print(f"  - {note}")
    if errors:
        print(f"FAIL ({len(errors)})")
        for error in errors:
            print(f"  - {error}")
    else:
        print("PASS")


if __name__ == "__main__":
    sys.exit(main())
