#!/usr/bin/env python3
"""Checks the Trial&Tally site before publishing. Run from anywhere: python3 _tools/check_site.py

- every internal link / src resolves to a file in the site (and #fragments exist)
- every English page has a Spanish page under /es/ and both link to each other
- no external URLs except mailto: and an App Store placeholder (apps.apple.com)
- no <script>, <form>, <iframe>, cookies, or external CSS/fonts
- basic accessibility: <html lang>, one <h1>, alt on every <img>
"""
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_EXTERNAL_HOSTS = {"apps.apple.com"}  # App Store link, once it exists
SKIP_DIRS = {".git", "_tools"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.tags = [], set(), []
        self.lang, self.h1, self.imgs_without_alt = None, 0, 0
        self.alternates = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and "alt" not in a:
            self.imgs_without_alt += 1
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
            self.alternates[a["hreflang"]] = a.get("href")
        for attr in ("href", "src", "action", "srcset", "poster"):
            if a.get(attr):
                self.links.append((tag, attr, a[attr]))


def site_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def resolve(page_rel, url):
    """Maps a site URL to a file path relative to ROOT (clean URLs -> folder/index.html)."""
    path = urlsplit(url).path
    if not path:
        return page_rel
    if not path.startswith("/"):
        path = "/" + os.path.normpath(os.path.join(os.path.dirname(page_rel), path))
    rel = path.lstrip("/")
    if rel == "" or rel.endswith("/"):
        return rel + "index.html"
    if os.path.splitext(rel)[1] == "":
        return rel + "/index.html"
    return rel


def main():
    errors, checked_links = [], 0
    files = sorted(site_files())
    html_files = [f for f in files if f.endswith(".html")]
    pages = {}
    for f in html_files:
        p = Page()
        with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
            text = fh.read()
        p.feed(text)
        pages[f] = (p, text)

    for f, (p, text) in pages.items():
        if not p.lang:
            errors.append(f"{f}: <html> has no lang")
        if p.h1 != 1:
            errors.append(f"{f}: expected exactly one <h1>, found {p.h1}")
        if p.imgs_without_alt:
            errors.append(f"{f}: {p.imgs_without_alt} <img> without alt")
        for bad in ("script", "form", "iframe", "object", "embed"):
            if bad in p.tags:
                errors.append(f"{f}: contains <{bad}>")
        if re.search(r"document\.cookie|set-cookie", text, re.I):
            errors.append(f"{f}: mentions cookies in code")
        for tag, attr, url in p.links:
            parts = urlsplit(url)
            if parts.scheme == "mailto":
                continue
            if parts.scheme or url.startswith("//"):
                if parts.hostname not in ALLOWED_EXTERNAL_HOSTS:
                    errors.append(f"{f}: external URL not allowed: {url}")
                continue
            checked_links += 1
            target = resolve(f, url)
            if not os.path.isfile(os.path.join(ROOT, target)):
                errors.append(f"{f}: broken link {url} -> {target}")
            elif parts.fragment and target in pages and parts.fragment not in pages[target][0].ids:
                errors.append(f"{f}: missing anchor {url}")
        # Any other absolute URL hiding in text/comments.
        for url in re.findall(r"https?://[^\s\"'<>)]+", text):
            if urlsplit(url).hostname not in ALLOWED_EXTERNAL_HOSTS:
                errors.append(f"{f}: external URL in page text: {url}")

    # CSS must not pull anything from outside.
    for f in files:
        if f.endswith(".css"):
            css = open(os.path.join(ROOT, f), encoding="utf-8").read()
            if re.search(r"@import|url\(\s*['\"]?(https?:)?//", css):
                errors.append(f"{f}: external CSS resource")

    # Spanish pairing.
    english = [f for f in html_files if not f.startswith("es/") and f != "404.html"]
    spanish = [f for f in html_files if f.startswith("es/")]
    for f in english:
        es = "es/" + f
        if es not in pages:
            errors.append(f"{f}: no Spanish page {es}")
            continue
        if resolve(f, pages[f][0].alternates.get("es", "")) != es:
            errors.append(f"{f}: language switcher doesn't point to {es}")
        if resolve(es, pages[es][0].alternates.get("en", "")) != f:
            errors.append(f"{es}: language switcher doesn't point to {f}")
        if pages[f][0].lang != "en" or pages[es][0].lang != "es":
            errors.append(f"{f}/{es}: wrong lang attribute")
    for f in spanish:
        if f[3:] not in pages:
            errors.append(f"{f}: no English page {f[3:]}")

    for required in ("CNAME", "404.html", "index.html", "privacy/index.html", "support/index.html", "terms/index.html"):
        if required not in files:
            errors.append(f"missing {required}")
    if "CNAME" in files and open(os.path.join(ROOT, "CNAME")).read().strip() != "trialandtally.com":
        errors.append("CNAME should contain trialandtally.com")

    print(f"{len(html_files)} HTML pages, {checked_links} internal links checked, "
          f"{len(english)} English / {len(spanish)} Spanish pages")
    for e in errors:
        print("ERROR:", e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
