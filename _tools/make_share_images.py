#!/usr/bin/env python3
"""Draws the 1200x630 link-preview images (Open Graph / Twitter / Facebook / iMessage):
assets/img/share-en.png and assets/img/share-es.png. Uses the dev venv's Playwright with the Mac's
Chrome (see README): .venv/bin/python _tools/make_share_images.py

Each card: the app icon and name, the headline, one line about the app, the price line, and an
iPhone showing the real session screenshot (01-session) in that language.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from devserver import Server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEXT = {
    "en": {"title": "Tap. Tally. Done.",
           "line": "Trial-by-trial accuracy and prompt levels for school SLPs, on iPhone and iPad.",
           "price": "7-day free trial · $4.99 once · No accounts, nothing kept"},
    "es": {"title": "Toca, cuenta y listo.",
           "line": "Precisión ensayo por ensayo y nivel de ayuda para terapeutas de lenguaje, en iPhone y iPad.",
           "price": "7 días gratis · $4.99 un solo pago · Nada se guarda"},
}

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><style>
html, body { margin: 0; }
body { width: 1200px; height: 630px; overflow: hidden; position: relative;
  font-family: -apple-system, BlinkMacSystemFont, "Helvetica Neue", Arial, sans-serif; color: #0f1b2d;
  background: radial-gradient(900px 500px at 95% -10%, rgba(36,104,206,.18), transparent 60%),
              radial-gradient(700px 420px at -10% 110%, rgba(46,156,79,.14), transparent 60%), #f7f9fd; }
.copy { position: absolute; left: 72px; top: 64px; width: 660px; }
.brand { display: flex; align-items: center; gap: 22px; font-size: 40px; font-weight: 800; letter-spacing: -.02em; }
.brand img { width: 112px; height: 112px; border-radius: 25px; box-shadow: 0 0 0 1px rgba(15,27,45,.08), 0 10px 30px rgba(36,104,206,.25); }
h1 { font-size: 92px; line-height: 1; font-weight: 850; letter-spacing: -.035em; word-spacing: .05em; margin: 44px 0 26px; }
p { font-size: 30px; line-height: 1.3; color: #3c4758; margin: 0 0 26px; }
.price { font-size: 25px; font-weight: 700; color: #0f1b2d; }
.bars { position: absolute; left: 0; right: 0; bottom: 0; height: 12px; display: flex; }
.bars i { flex: 1; } .r { background: #c0262d; } .y { background: #f6c324; } .g { background: #1b7a34; } .b { background: #2468ce; }
.phone { position: absolute; right: 70px; top: 46px; width: 340px; padding: 12px; border-radius: 54px;
  background: #0c0f14; box-shadow: 0 30px 70px rgba(15,27,45,.30), inset 0 0 0 2px #2a2f38; }
.phone img { display: block; width: 100%; border-radius: 43px; }
.phone::before { content: ""; position: absolute; left: 50%; transform: translateX(-50%); top: 22px;
  width: 92px; height: 27px; border-radius: 99px; background: #0c0f14; }
</style></head><body>
<div class="copy">
  <div class="brand"><img src="/assets/img/icon-384.png" alt="">Trial&amp;Tally</div>
  <h1>{title}</h1>
  <p>{line}</p>
  <div class="price">{price}</div>
</div>
<div class="phone"><img src="/assets/img/shots/{lang}/01-session-900.webp" alt=""></div>
<div class="bars"><i class="r"></i><i class="y"></i><i class="g"></i><i class="b"></i></div>
</body></html>"""


def main():
    with Server() as base, sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        for lang, t in TEXT.items():
            page.goto(base + "/assets/site.css")  # any same-origin URL, so /assets paths resolve
            html = TEMPLATE.replace("{lang}", lang)
            for key, value in t.items():
                html = html.replace("{" + key + "}", value)
            page.set_content(html, wait_until="networkidle")
            out = os.path.join(ROOT, "assets", "img", f"share-{lang}.png")
            page.screenshot(path=out, clip={"x": 0, "y": 0, "width": 1200, "height": 630})
            print("wrote", os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, "KB")
        browser.close()


if __name__ == "__main__":
    main()
