"""Measures what the home page actually transfers in Chrome, before the video: first view, and
after scrolling the whole page (every lazy image loaded). Budget: 400 KB. The numbers are written
to _review/weight.json for the report. Local server = no gzip, so this overstates text files a
little compared with GitHub Pages."""
import json
import os

import pytest
from conftest import LANGS, ROOT, scroll_through

BUDGET = 400 * 1024
CASES = {
    "phone-3x": {"viewport": {"width": 375, "height": 812}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
    "chromebook-1x": {"viewport": {"width": 1366, "height": 768}, "device_scale_factor": 1},
    "desktop-2x": {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 2},
}
RESULTS = {}

TRANSFERRED = """() => {
  const nav = performance.getEntriesByType('navigation')[0];
  const res = performance.getEntriesByType('resource').filter(r => !/\\.(mp4|webm|mov)$/.test(r.name));
  return {bytes: nav.transferSize + res.reduce((s, r) => s + r.transferSize, 0), requests: res.length + 1,
          video: performance.getEntriesByType('resource').filter(r => /\\.mp4$/.test(r.name)).length};
}"""


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("lang", list(LANGS))
def test_home_weight(browser, base_url, lang, case):
    opts = dict(CASES[case])
    viewport = opts.pop("viewport")
    # Reduced motion keeps the video from starting while we scroll past it.
    context = browser.new_context(viewport=viewport, reduced_motion="reduce", **opts)
    page = context.new_page()
    page.goto(base_url + LANGS[lang], wait_until="load")
    page.wait_for_timeout(300)
    first = page.evaluate(TRANSFERRED)
    first_view_ms = page.evaluate("performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd")
    scroll_through(page, step=400, pause=60)
    page.wait_for_load_state("networkidle")
    full = page.evaluate(TRANSFERRED)
    context.close()
    RESULTS[f"{lang} {case}"] = {"first_view_kb": round(first["bytes"] / 1024, 1),
                                 "whole_page_kb": round(full["bytes"] / 1024, 1),
                                 "requests": full["requests"], "dom_content_loaded_ms": round(first_view_ms)}
    os.makedirs(os.path.join(ROOT, "_review"), exist_ok=True)
    with open(os.path.join(ROOT, "_review", "weight.json"), "w") as fh:
        json.dump(RESULTS, fh, indent=2)
    print(lang, case, RESULTS[f"{lang} {case}"])
    assert full["video"] == 0
    assert first["bytes"] < BUDGET
    assert full["bytes"] < BUDGET
