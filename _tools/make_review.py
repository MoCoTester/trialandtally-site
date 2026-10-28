#!/usr/bin/env python3
"""Review copies in _review/ (git-ignored, never published).

  python3 _tools/make_review.py            plain-text copies of the English Privacy, Terms and
                                           Support pages (standard library only)
  .venv/bin/python _tools/make_review.py --screens
                                           also screenshots: full-page home in English and Spanish
                                           at phone and desktop sizes, first views, the demo after a
                                           few taps, the share images, and the restyled subpages
                                           (needs the dev venv; see README)
"""
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


PHONE = {"width": 375, "height": 812}
CHROMEBOOK = {"width": 1366, "height": 768}
DESKTOP = {"width": 1440, "height": 900}
# Review shots show the poster, not a playing video.
NO_AUTOPLAY = "HTMLMediaElement.prototype.play = function () { return Promise.resolve(); };"


def settle(page, scroll=True):
    if scroll:  # load the lazy images
        height = page.evaluate("document.documentElement.scrollHeight")
        for y in range(0, height + 500, 500):
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(50)
        page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1800)  # icon animation finished


def stitched(page, path):
    """Full page as the viewer scrolls it, one screen at a time (the sticky phone in "How it
    works" needs a real viewport height, and Chrome can't capture more than ~16,000 px in one
    shot). The header is unstuck for this so it shows once, at the top."""
    from PIL import Image
    import io
    page.add_style_tag(content=".site-header { position: static !important; }")
    vh = page.viewport_size["height"]
    height = page.evaluate("document.documentElement.scrollHeight")
    scale = page.evaluate("devicePixelRatio")
    canvas = Image.new("RGB", (round(page.viewport_size["width"] * scale), round(height * scale)), "white")
    y = 0
    while y < height:
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(350)
        actual = page.evaluate("window.scrollY")
        tile = Image.open(io.BytesIO(page.screenshot()))
        canvas.paste(tile, (0, round(actual * scale)))
        y += vh
    canvas.save(path)


def screens():
    import shutil
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from devserver import Server
    from playwright.sync_api import sync_playwright

    out = os.path.join(ROOT, "_review")
    written = []

    def shot(name):
        path = os.path.join(out, name)
        written.append(path)
        return path

    with Server() as base, sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")  # one browser for everything

        def new_page(viewport, scale=2):
            context = browser.new_context(viewport=viewport, device_scale_factor=scale)
            context.add_init_script(NO_AUTOPLAY)
            return context, context.new_page()

        for lang, path in (("en", "/"), ("es", "/es/")):
            ctx, page = new_page(PHONE)
            page.goto(base + path)
            settle(page)
            stitched(page, shot(f"home-{lang}-phone.png"))
            ctx.close()
        for lang, path in (("en", "/"), ("es", "/es/")):
            ctx, page = new_page(DESKTOP, scale=1)
            page.goto(base + path)
            settle(page)
            stitched(page, shot(f"home-{lang}-desktop.png"))
            ctx.close()
        for lang, path in (("en", "/"), ("es", "/es/")):
            for label, viewport in (("phone", PHONE), ("chromebook", CHROMEBOOK)):
                ctx, page = new_page(viewport, scale=2 if label == "phone" else 1)
                page.goto(base + path)
                settle(page, scroll=False)
                page.screenshot(path=shot(f"first-view-{lang}-{label}.png"))
                ctx.close()
        for lang, path, prompt in (("en", "/", "Verbal"), ("es", "/es/", "Verbal")):
            ctx, page = new_page(PHONE)
            page.goto(base + path)
            demo = page.locator("#demo-app")
            main = '[data-step="main"] '
            for action in ("correct", "correct", "prompted", "incorrect"):
                if action == "prompted":
                    demo.locator(main + '[data-action="prompted"]').click()
                    demo.locator(f'[data-prompt="{prompt}"]').click()
                    demo.locator('[data-step="result"] [data-record="promptedCorrect"]').click()
                else:
                    demo.locator(main + f'[data-record="{action}"]').click()
            demo.locator(main + '[data-action="prompted"]').click()
            demo.scroll_into_view_if_needed()
            demo.screenshot(path=shot(f"demo-{lang}-prompt-step.png"))
            demo.locator('[data-action="cancel"]').first.click()
            page.locator("#demo-summary-btn").click()
            page.wait_for_timeout(200)
            demo.screenshot(path=shot(f"demo-{lang}-after-taps.png"))
            ctx.close()
        for sub, viewport, label in (("support/", DESKTOP, "desktop"), ("es/privacy/", PHONE, "phone"),
                                     ("terms/", PHONE, "phone"), ("no-such-page/", DESKTOP, "desktop")):
            ctx, page = new_page(viewport, scale=1 if label == "desktop" else 2)
            page.goto(base + "/" + sub)
            name = sub.strip("/").replace("/", "-").replace("no-such-page", "404")
            page.screenshot(path=shot(f"page-{name}-{label}.png"), full_page=True)
            ctx.close()
        ctx, page = new_page(PHONE)
        page.emulate_media(color_scheme="dark")
        page.goto(base + "/")
        settle(page)
        stitched(page, shot("home-en-phone-dark.png"))
        ctx.close()
        browser.close()
    for lang in ("en", "es"):
        dest = shot(f"share-{lang}.png")
        shutil.copy(os.path.join(ROOT, "assets", "img", f"share-{lang}.png"), dest)
    for path in written:
        print("wrote", path)


def main():
    import sys
    os.makedirs(os.path.join(ROOT, "_review"), exist_ok=True)
    for name, rel in PAGES.items():
        path = os.path.join(ROOT, "_review", f"{name}.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(name, rel))
        print("wrote", os.path.relpath(path, ROOT))
    if "--screens" in sys.argv:
        screens()


if __name__ == "__main__":
    main()
