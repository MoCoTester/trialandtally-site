#!/usr/bin/env python3
"""Checks the Trial&Tally site before publishing. Standard library only; run from anywhere:
python3 _tools/check_site.py   (prints OK, or every problem and exits 1)

For every published page in both languages:
- internal links, src/srcset/poster and #anchors resolve (own-domain https://trialandtally.com
  URLs are resolved locally too); no duplicate ids
- every <img> has alt; every <video> has an accessible name; one <h1>; headings don't skip levels
- required <head> tags: charset, viewport, title, description, color-scheme; and (except 404)
  canonical, hreflang en/es/x-default pairs that point at each other, Open Graph and Twitter tags
  whose share image exists and is 1200x630
- nothing loads from another site: every resource URL in HTML and CSS is local; links to other
  sites only to mailto: and the App Store; no cookies/storage/network APIs in JS; no inline JS
- page weight budget (home page, everything except the video) and CNAME intact
- the pages are up to date with _src/ (python3 _tools/build.py --check)
"""
import os
import re
import struct
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_HOST = "trialandtally.com"
LINK_ONLY_HOSTS = {"apps.apple.com"}  # may be linked (<a href>), never loaded
SKIP_DIRS = {".git", "_tools", "_src", "_review", ".venv", "node_modules"}
HOME_BUDGET = 400 * 1024  # bytes, before the video (uncompressed; GitHub Pages also gzips text)
REQUIRED_PAGES = ["index.html", "support/index.html", "privacy/index.html", "terms/index.html",
                  "es/index.html", "es/support/index.html", "es/privacy/index.html", "es/terms/index.html",
                  "404.html"]
FORBIDDEN_JS = [r"document\.cookie", r"localStorage", r"sessionStorage", r"indexedDB", r"\bfetch\s*\(",
                r"XMLHttpRequest", r"WebSocket", r"sendBeacon", r"EventSource", r"https?://"]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.resources, self.anchors, self.ids, self.dup_ids = [], [], set(), set()
        self.lang, self.headings, self.tags = None, [], []
        self.imgs_without_alt, self.videos_without_name = 0, 0
        self.alternates, self.canonical, self.meta, self.title = {}, None, {}, None
        self.forms, self._in_title, self.inline_js, self.charset = [], False, 0, False

    def handle_starttag(self, tag, attrs):
        names = {k for k, _ in attrs}
        a = {k: (v or "") for k, v in attrs}
        self.tags.append(tag)
        if "id" in a:
            (self.dup_ids if a["id"] in self.ids else self.ids).add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if re.fullmatch(r"h[1-6]", tag):
            self.headings.append(int(tag[1]))
        if tag == "title":
            self._in_title = True
        if tag == "img" and "alt" not in names:
            self.imgs_without_alt += 1
        if tag == "video" and not (a.get("aria-label") or a.get("aria-labelledby") or a.get("title")):
            self.videos_without_name += 1
        if tag == "meta":
            if "charset" in a:
                self.charset = True
            key = a.get("name") or a.get("property")
            if key:
                self.meta.setdefault(key, a.get("content", ""))
        if tag == "link":
            rel = a.get("rel", "")
            if rel == "alternate" and a.get("hreflang"):
                self.alternates[a["hreflang"]] = a.get("href")
            elif rel == "canonical":
                self.canonical = a.get("href")
            else:
                self.resources.append((tag, "href", a.get("href", "")))
        if tag == "script":
            if a.get("src"):
                self.resources.append((tag, "src", a["src"]))
            elif a.get("type") != "application/json":
                self.inline_js += 1
        if tag == "form":
            self.forms.append(a)
        if tag == "a" and a.get("href"):
            self.anchors.append(a["href"])
        for attr in ("src", "poster"):
            if tag in ("img", "source", "video", "audio", "iframe", "embed", "track") and a.get(attr):
                self.resources.append((tag, attr, a[attr]))
        if a.get("srcset"):
            for part in a["srcset"].split(","):
                self.resources.append((tag, "srcset", part.strip().split(" ")[0]))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data


def site_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if not name.startswith("."):
                yield os.path.relpath(os.path.join(dirpath, name), ROOT)


def resolve(page_rel, url):
    """Maps a site URL to a file path relative to ROOT (clean URLs -> folder/index.html)."""
    parts = urlsplit(url)
    path = parts.path
    if parts.scheme in ("http", "https"):
        path = path or "/"
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


def is_own(url):
    parts = urlsplit(url)
    return (not parts.scheme and not url.startswith("//")) or parts.hostname == SITE_HOST


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def module_imports(js_rel):
    """Local modules a script imports (static imports only)."""
    text = open(os.path.join(ROOT, js_rel), encoding="utf-8").read()
    return [os.path.normpath(os.path.join(os.path.dirname(js_rel), spec))
            for spec in re.findall(r"""import\s[^'"]*?from\s*['"]([^'"]+)['"]""", text)]


def page_weight(rel):
    """Bytes for a page's HTML, CSS, JS (with imports) and images, excluding video files. For each
    <picture>, the largest file of its first <source> (the AVIF set, what Chrome and Safari load)."""
    text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    picked = []
    for picture in re.findall(r"<picture.*?</picture>", text, re.S):
        first = re.search(r'srcset="([^"]+)"', picture).group(1)
        picked.append(max((c.strip().split(" ")[0] for c in first.split(",")),
                          key=lambda u: os.path.getsize(os.path.join(ROOT, resolve(rel, u)))))
    rest = Page()
    rest.feed(re.sub(r"<picture.*?</picture>", "", text, flags=re.S))
    queue = [resolve(rel, u) for _, _, u in rest.resources if is_own(u)]
    queue += [resolve(rel, u) for u in picked]
    seen, total = set(), os.path.getsize(os.path.join(ROOT, rel))
    while queue:
        target = queue.pop()
        if target in seen or target.endswith((".mp4", ".webm", ".mov")):
            continue
        seen.add(target)
        path = os.path.join(ROOT, target)
        if os.path.isfile(path):
            total += os.path.getsize(path)
            if target.endswith(".js"):
                queue += module_imports(target)
    return total


def main():
    errors, checked = [], 0
    files = sorted(site_files())
    html_files = [f for f in files if f.endswith(".html")]
    pages = {}
    for f in html_files:
        p = Page()
        with open(os.path.join(ROOT, f), encoding="utf-8") as fh:
            text = fh.read()
        p.feed(text)
        pages[f] = (p, text)

    for required in REQUIRED_PAGES + ["CNAME"]:
        if required not in files:
            errors.append(f"missing {required}")
    if "CNAME" in files and open(os.path.join(ROOT, "CNAME")).read() != "trialandtally.com\n":
        errors.append("CNAME must contain exactly 'trialandtally.com'")

    for f, (p, text) in pages.items():
        is_404 = f == "404.html"
        if p.lang not in ("en", "es"):
            errors.append(f"{f}: <html lang> should be en or es, is {p.lang!r}")
        if p.headings.count(1) != 1:
            errors.append(f"{f}: expected exactly one <h1>, found {p.headings.count(1)}")
        if p.headings and p.headings[0] != 1:
            errors.append(f"{f}: first heading should be <h1>")
        for prev, cur in zip(p.headings, p.headings[1:]):
            if cur > prev + 1:
                errors.append(f"{f}: heading level jumps from h{prev} to h{cur}")
                break
        if p.imgs_without_alt:
            errors.append(f"{f}: {p.imgs_without_alt} <img> without alt")
        if p.videos_without_name:
            errors.append(f"{f}: <video> without an accessible name")
        if p.dup_ids:
            errors.append(f"{f}: duplicate ids {sorted(p.dup_ids)}")
        for bad in ("iframe", "object", "embed", "applet"):
            if bad in p.tags:
                errors.append(f"{f}: contains <{bad}>")
        for form in p.forms:
            if form.get("method") != "dialog":
                errors.append(f"{f}: <form> that submits somewhere (only method=dialog allowed)")
        if p.inline_js:
            errors.append(f"{f}: inline <script> code (only external modules and application/json data)")
        if re.search(r"document\.cookie|localStorage|sessionStorage", text):
            errors.append(f"{f}: mentions cookies/storage in code")

        # Head
        if not p.charset:
            errors.append(f"{f}: no <meta charset>")
        for name in ("viewport", "description", "color-scheme"):
            if not p.meta.get(name):
                errors.append(f"{f}: missing <meta name={name}>")
        if not (p.title or "").strip():
            errors.append(f"{f}: missing <title>")
        if is_404:
            if "noindex" not in p.meta.get("robots", ""):
                errors.append("404.html: should be noindex")
        else:
            own_url = f"https://{SITE_HOST}/" + (f[:-len("index.html")] if f.endswith("index.html") else f)
            if p.canonical != own_url:
                errors.append(f"{f}: canonical should be {own_url}, is {p.canonical}")
            for prop in ("og:type", "og:site_name", "og:title", "og:description", "og:url", "og:image",
                         "og:image:width", "og:image:height", "og:image:alt", "og:locale",
                         "twitter:card", "twitter:title", "twitter:description", "twitter:image",
                         "twitter:image:alt"):
                if not p.meta.get(prop):
                    errors.append(f"{f}: missing {prop}")
            if p.meta.get("og:url") != own_url:
                errors.append(f"{f}: og:url should be {own_url}")
            if p.meta.get("twitter:card") != "summary_large_image":
                errors.append(f"{f}: twitter:card should be summary_large_image")
            image = p.meta.get("og:image", "")
            if not image.startswith(f"https://{SITE_HOST}/"):
                errors.append(f"{f}: og:image must be an absolute https://{SITE_HOST}/ URL")
            else:
                img_path = os.path.join(ROOT, resolve(f, image))
                if not os.path.isfile(img_path):
                    errors.append(f"{f}: og:image file missing: {image}")
                elif png_size(img_path) != (1200, 630):
                    errors.append(f"{f}: og:image should be a 1200x630 PNG, is {png_size(img_path)}")
            expected_locale = "es_MX" if p.lang == "es" else "en_US"
            if p.meta.get("og:locale") != expected_locale:
                errors.append(f"{f}: og:locale should be {expected_locale}")

        # Resources: local only, and they exist.
        for tag, attr, url in p.resources:
            if url.startswith("data:"):
                continue
            if not is_own(url):
                errors.append(f"{f}: loads from another site: <{tag} {attr}={url}>")
                continue
            checked += 1
            target = resolve(f, url)
            if not os.path.isfile(os.path.join(ROOT, target)):
                errors.append(f"{f}: missing file {url} -> {target}")
        # Links
        for url in p.anchors:
            parts = urlsplit(url)
            if parts.scheme == "mailto":
                if parts.path != "support@trialandtally.com":
                    errors.append(f"{f}: unexpected email link {url}")
                continue
            if not is_own(url):
                if parts.scheme != "https" or parts.hostname not in LINK_ONLY_HOSTS:
                    errors.append(f"{f}: link to another site not allowed: {url}")
                continue
            checked += 1
            target = resolve(f, url)
            if not os.path.isfile(os.path.join(ROOT, target)):
                errors.append(f"{f}: broken link {url} -> {target}")
            elif parts.fragment:
                ids = pages[target][0].ids if target in pages else set()
                if parts.fragment not in ids:
                    errors.append(f"{f}: missing anchor {url}")
        # Any other absolute URL hiding in the page (comments, text, attributes).
        for url in re.findall(r"https?://[^\s\"'<>)]+", text):
            host = urlsplit(url).hostname
            if host != SITE_HOST and host not in LINK_ONLY_HOSTS:
                errors.append(f"{f}: URL to another site in page: {url}")

    # hreflang pairs: every English page has a Spanish twin, and they point at each other.
    english = [f for f in html_files if not f.startswith("es/") and f != "404.html"]
    spanish = [f for f in html_files if f.startswith("es/")]
    for f in english:
        es = "es/" + f
        if es not in pages:
            errors.append(f"{f}: no Spanish page {es}")
            continue
        for page_rel in (f, es):
            alts = pages[page_rel][0].alternates
            if set(alts) != {"en", "es", "x-default"}:
                errors.append(f"{page_rel}: hreflang should be en, es and x-default, is {sorted(alts)}")
                continue
            if resolve(page_rel, alts["en"]) != f or resolve(page_rel, alts["es"]) != es:
                errors.append(f"{page_rel}: hreflang pair should be {f} / {es}")
            if resolve(page_rel, alts["x-default"]) != f:
                errors.append(f"{page_rel}: x-default should be the English page")
            if not all(v.startswith(f"https://{SITE_HOST}/") for v in alts.values()):
                errors.append(f"{page_rel}: hreflang URLs must be absolute")
        # The visible language switch goes to the twin page.
        for page_rel, twin, other in ((f, es, "es"), (es, f, "en")):
            switch = re.search(r'<nav class="lang"[^>]*>\s*<a href="([^"]+)" hreflang="(\w+)"', pages[page_rel][1])
            if not switch or resolve(page_rel, switch.group(1)) != twin or switch.group(2) != other:
                errors.append(f"{page_rel}: language switch should go to {twin}")
        if pages[f][0].lang != "en" or pages[es][0].lang != "es":
            errors.append(f"{f}/{es}: wrong lang attribute")
    for f in spanish:
        if f[3:] not in pages:
            errors.append(f"{f}: no English page {f[3:]}")

    # CSS: nothing from outside.
    for f in files:
        if f.endswith(".css"):
            css = open(os.path.join(ROOT, f), encoding="utf-8").read()
            if "@import" in css:
                errors.append(f"{f}: @import not allowed")
            for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", css):
                if not url.startswith("data:") and not is_own(url):
                    errors.append(f"{f}: external CSS resource {url}")
    # JS: no network, storage or cookies.
    for f in files:
        if f.endswith(".js"):
            js = open(os.path.join(ROOT, f), encoding="utf-8").read()
            code = re.sub(r"(?m)^\s*//[^\n]*|/\*.*?\*/", "", js, flags=re.S)
            for pattern in FORBIDDEN_JS:
                if re.search(pattern, code):
                    errors.append(f"{f}: forbidden in site JS: {pattern}")

    # Weight budget (home pages).
    weights = {}
    for f in ("index.html", "es/index.html"):
        if f in pages:
            weights[f] = page_weight(f)
            if weights[f] > HOME_BUDGET:
                errors.append(f"{f}: page weight {weights[f] / 1024:.0f} KB is over the {HOME_BUDGET // 1024} KB budget")

    # Generated pages match their sources.
    result = subprocess.run([sys.executable, os.path.join(ROOT, "_tools", "build.py"), "--check"],
                            capture_output=True, text=True)
    if result.returncode != 0:
        errors.append("pages are out of date with _src/: run python3 _tools/build.py")

    print(f"{len(html_files)} HTML pages, {checked} internal links/resources checked, "
          f"{len(english)} English / {len(spanish)} Spanish pages")
    for f, w in weights.items():
        print(f"{f}: {w / 1024:.0f} KB before the video (budget {HOME_BUDGET // 1024} KB, uncompressed, largest images)")
    for e in errors:
        print("ERROR:", e)
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
