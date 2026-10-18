#!/usr/bin/env python3
"""Writes plain-text review copies of the English Privacy, Terms, and Support pages to
_review/ (git-ignored, never published). Run: python3 _tools/make_review.py"""
import os
import re
import textwrap
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {"privacy": "privacy/index.html", "terms": "terms/index.html", "support": "support/index.html"}
WIDTH = 90


class MainText(HTMLParser):
    """Collects (kind, text) blocks from inside <main>."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main, self.blocks, self.kind, self.buf = False, [], None, []

    def handle_starttag(self, tag, attrs):
        if tag == "main":
            self.in_main = True
        elif self.in_main and tag in ("h1", "h2", "h3", "p", "li"):
            self.kind, self.buf = tag, []

    def handle_endtag(self, tag):
        if tag == "main":
            self.in_main = False
        elif self.in_main and tag == self.kind:
            text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if text:
                self.blocks.append((self.kind, text))
            self.kind = None

    def handle_data(self, data):
        if self.kind:
            self.buf.append(data)


def render(name, rel):
    parser = MainText()
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        parser.feed(fh.read())
    out = [f"DRAFT FOR REVIEW - plain-text copy of https://trialandtally.com/{name} (not published)", ""]
    for kind, text in parser.blocks:
        if kind == "h1":
            out += [text.upper(), "=" * len(text), ""]
        elif kind == "h2":
            out += [text, "-" * len(text), ""]
        elif kind == "li":
            out += textwrap.wrap(text, WIDTH, initial_indent="  - ", subsequent_indent="    ") + [""]
        else:
            out += textwrap.wrap(text, WIDTH) + [""]
    return "\n".join(out).rstrip() + "\n"


def main():
    os.makedirs(os.path.join(ROOT, "_review"), exist_ok=True)
    for name, rel in PAGES.items():
        path = os.path.join(ROOT, "_review", f"{name}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(name, rel))
        print("wrote", os.path.relpath(path, ROOT))


if __name__ == "__main__":
    main()
