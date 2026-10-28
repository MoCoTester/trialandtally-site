"""Shared fixtures: one local server (a stand-in for trialandtally.com) and ONE headless Chrome
for the whole run (memory: never more than one browser at a time). Pages are opened in fresh
contexts, so no state carries between tests.

Every page opened through `open_page` records console errors and every request; tests call
`assert_clean(page)` to check there were no errors and no request left the local server."""
import os
import sys
from urllib.parse import urlsplit

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
from devserver import Server  # noqa: E402

AXE = os.path.join(TOOLS, ".cache", "axe-core-4.14.0", "axe.min.js")

VIEWPORTS = {
    "phone": {"width": 375, "height": 812},
    "chromebook": {"width": 1366, "height": 768},
    "desktop": {"width": 1440, "height": 900},
}
LANGS = {"en": "/", "es": "/es/"}


@pytest.fixture(scope="session")
def base_url():
    with Server() as url:
        yield url


@pytest.fixture(scope="session")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="chrome", headless=True)
        except Exception:  # no Google Chrome: fall back to Playwright's own Chromium if installed
            b = p.chromium.launch(headless=True)
        yield b
        b.close()


@pytest.fixture
def open_page(browser, base_url):
    contexts = []

    def _open(path="/", viewport="phone", reduced_motion="no-preference", color_scheme="light", wait="load", **ctx):
        size = VIEWPORTS[viewport] if isinstance(viewport, str) else viewport
        context = browser.new_context(viewport=size, reduced_motion=reduced_motion, color_scheme=color_scheme, **ctx)
        contexts.append(context)
        page = context.new_page()
        page.errors, page.requests = [], []
        page.on("console", lambda m: m.type == "error" and page.errors.append(m.text))
        page.on("pageerror", lambda e: page.errors.append(str(e)))
        page.on("request", lambda r: page.requests.append(r.url))
        page.base = base_url
        if path is not None:
            page.goto(base_url + path, wait_until=wait)
        return page

    yield _open
    for c in contexts:
        c.close()


def external_requests(page):
    own = urlsplit(page.base).netloc
    return [u for u in page.requests
            if not u.startswith(("data:", "blob:", "about:")) and urlsplit(u).netloc != own]


def assert_clean(page):
    assert page.errors == [], f"console errors: {page.errors}"
    assert external_requests(page) == [], f"requests outside the site: {external_requests(page)}"


def scroll_through(page, step=500, pause=40):
    """Scrolls to the bottom in steps (loads lazy images), then back to the top."""
    height = page.evaluate("document.documentElement.scrollHeight")
    for y in range(0, height + step, step):
        page.evaluate(f"window.scrollTo(0, {y})")
        page.wait_for_timeout(pause)
    page.evaluate("window.scrollTo(0, 0)")


def run_axe(page, context=None):
    """Runs axe-core (WCAG 2.x A/AA + best practices). Returns serious/critical violations."""
    if not os.path.exists(AXE):
        pytest.fail("axe-core missing: run bash _tools/setup_dev.sh")
    page.add_script_tag(path=AXE)
    result = page.evaluate(
        """async (ctx) => await axe.run(ctx || document, {
             runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']},
             resultTypes: ['violations']})""", context)
    return [
        {"id": v["id"], "impact": v["impact"], "help": v["help"],
         "nodes": [n["target"] for n in v["nodes"]][:5]}
        for v in result["violations"] if v["impact"] in ("serious", "critical")
    ]
