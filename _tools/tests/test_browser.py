"""Browser tests in headless Chrome against the local server (standing in for trialandtally.com).

English and Spanish, at phone (375x812), Chromebook (1366x768) and desktop (1440x900) sizes:
no console errors, no requests outside the site, no horizontal scroll at 320 px, the live demo
(mouse and keyboard), the calculator, reduced motion, the lazy video, the language switch, and
axe-core accessibility checks."""
import re

import pytest
from playwright.sync_api import expect
from conftest import LANGS, VIEWPORTS, assert_clean, external_requests, run_axe, scroll_through

ALL_PAGES = ["/", "/support/", "/privacy/", "/terms/", "/es/", "/es/support/", "/es/privacy/", "/es/terms/"]

DEMO = {
    "en": {"correct": "Correct", "incorrect": "Incorrect", "prompted": "Prompted", "verbal": "Verbal",
           "see": "See summary", "hide": "Hide summary", "end": "End & Clear", "cancel": "Cancel",
           "counts": "{c} of {t} correct on own · {p} prompted", "none": "No trials yet",
           "pct": "{n}%", "live_pct": "{n} percent", "cleared": "Demo cleared"},
    "es": {"correct": "Correcto", "incorrect": "Incorrecto", "prompted": "Con ayuda", "verbal": "Verbal",
           "see": "Ver resumen", "hide": "Ocultar resumen", "end": "Terminar y borrar", "cancel": "Cancelar",
           "counts": None, "none": "Aún no hay ensayos",
           "pct": "{n} %", "live_pct": "{n} por ciento", "cleared": "Demostración borrada"},
}


def counts(lang, c, t, p):
    if lang == "en":
        return f"{c} of {t} correct on own · {p} prompted"
    return f"{c} de {t} {'correcto' if c == 1 else 'correctos'} sin ayuda · {p} con ayuda"


def demo_state(page):
    return (page.locator("#demo-pct span[aria-hidden]").inner_text(), page.locator("#demo-counts").inner_text())


def expect_state(page, pct, counts_text):
    """Waits (up to 2 s) for the goal card to show this percentage and counts line."""
    expect(page.locator("#demo-pct span[aria-hidden]")).to_have_text(pct, timeout=2000)
    expect(page.locator("#demo-counts")).to_have_text(counts_text, timeout=2000)


# ---------------------------------------------------------------- loading


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize("lang", list(LANGS))
def test_home_loads_clean(open_page, lang, viewport):
    page = open_page(LANGS[lang], viewport=viewport)
    scroll_through(page)
    page.wait_for_timeout(300)
    assert_clean(page)
    assert page.locator("h1").count() == 1
    assert page.evaluate("document.documentElement.scrollWidth") <= VIEWPORTS[viewport]["width"]
    # Every image that loaded actually decoded (no broken images).
    broken = page.evaluate("Array.from(document.images).filter(i => i.complete && i.loading !== 'lazy' && i.naturalWidth === 0).map(i => i.currentSrc)")
    assert broken == []


@pytest.mark.parametrize("path", ALL_PAGES)
def test_every_page_clean(open_page, path):
    page = open_page(path)
    assert_clean(page)
    assert page.evaluate("document.cookie") == ""


def test_missing_page_shows_404(open_page):
    page = open_page(None)
    response = page.goto(page.base + "/no-such-page/")
    assert response.status == 404
    assert "Page not found" in page.locator("h1").inner_text()
    # The only console message allowed is Chrome noting the page's own 404 status.
    page.errors = [e for e in page.errors if "status of 404" not in e]
    assert_clean(page)


@pytest.mark.parametrize("path", ALL_PAGES + ["/404.html"])
def test_no_horizontal_scroll_at_320(open_page, path):
    page = open_page(path, viewport={"width": 320, "height": 640})
    assert page.evaluate("document.documentElement.scrollWidth") <= 320
    if path in ("/", "/es/"):
        # Also with the demo's longest content showing: prompt step, summary open, dialog open.
        lang = "es" if path == "/es/" else "en"
        demo = page.locator("#demo-app")
        demo.locator('[data-step="main"] [data-record="correct"]').click()
        demo.locator('[data-action="prompted"]').click()
        assert page.evaluate("document.documentElement.scrollWidth") <= 320
        demo.locator('[data-prompt="Verbal"]').click()
        assert page.evaluate("document.documentElement.scrollWidth") <= 320
        demo.locator('[data-step="result"] [data-record="promptedIncorrect"]').click()
        page.locator("#demo-summary-btn").click()
        assert page.evaluate("document.documentElement.scrollWidth") <= 320
        page.locator("#demo-clear").click()
        assert page.locator("#demo-confirm").is_visible()
        assert page.evaluate("document.documentElement.scrollWidth") <= 320
        page.get_by_role("button", name=DEMO[lang]["cancel"], exact=True).last.click()


# ---------------------------------------------------------------- demo


@pytest.mark.parametrize("viewport", list(VIEWPORTS))
@pytest.mark.parametrize("lang", list(LANGS))
def test_demo_flow(open_page, lang, viewport):
    t = DEMO[lang]
    page = open_page(LANGS[lang], viewport=viewport)
    demo = page.locator("#demo-app")
    assert demo.get_attribute("data-ready") == "true"
    live = page.locator("#demo-live")
    pct = lambda n: t["pct"].format(n=n)  # noqa: E731

    expect_state(page, "–", t["none"])
    assert page.locator("#demo-undo").is_disabled()

    demo.locator('[data-step="main"] [data-record="correct"]').click()
    expect_state(page, pct(100), counts(lang, 1, 1, 0))
    page.wait_for_function("document.querySelector('#demo-live').textContent.length > 0")
    assert t["live_pct"].format(n=100) in live.inner_text()

    demo.locator('[data-step="main"] [data-action="prompted"]').click()
    assert demo.locator('[data-step="choose"]').is_visible()
    assert not demo.locator('[data-step="main"]').is_visible()
    demo.locator('[data-prompt="Verbal"]').click()
    assert t["verbal"] in demo.locator('[data-step="result"] .step-label').inner_text()
    demo.locator('[data-step="result"] [data-record="promptedCorrect"]').click()
    expect_state(page, pct(50), counts(lang, 1, 2, 1))
    assert demo.locator('[data-step="main"]').is_visible()

    demo.locator('[data-step="main"] [data-record="incorrect"]').click()
    expect_state(page, pct(33), counts(lang, 1, 3, 1))
    page.wait_for_function(f"document.querySelector('#demo-live').textContent.includes('{t['live_pct'].format(n=33)}')")

    page.locator("#demo-undo").click()
    expect_state(page, pct(50), counts(lang, 1, 2, 1))
    demo.locator('[data-step="main"] [data-record="incorrect"]').click()

    # Second student: separate tallies and separate undo.
    page.locator("#demo-tab-1").click()
    assert page.locator("#demo-tab-1").get_attribute("aria-selected") == "true"
    expect_state(page, "–", t["none"])
    assert page.locator("#demo-undo").is_disabled()
    demo.locator('[data-step="main"] [data-record="correct"]').click()
    expect_state(page, pct(100), counts(lang, 1, 1, 0))
    page.locator("#demo-tab-0").click()
    expect_state(page, pct(33), counts(lang, 1, 3, 1))

    # Summary in the app's plain-text format.
    button = page.locator("#demo-summary-btn")
    button.click()
    assert button.inner_text() == t["hide"] and button.get_attribute("aria-expanded") == "true"
    text = page.locator("#demo-summary-text").inner_text()
    expected = {
        "en": ["STUDENT: AB", "Goal 1: /r/ initial – words",
               "  Accuracy: 33%  (1 of 3 correct on own)",
               "  Correct on own ........  1  (33%)",
               "  Prompted – correct ....  1  (33%)",
               "  Prompted – incorrect ..  0   (0%)",
               "  Incorrect, no prompt ..  1  (33%)",
               "  Prompts used (1):",
               "    Verbal 1  (1 correct, 0 incorrect)",
               "", "STUDENT: CD", "Goal 1: Following 2-step directions",
               "  Accuracy: 100%  (1 of 1 correct on own)"],
        "es": ["ESTUDIANTE: AB", "Objetivo 1: /r/ inicial – palabras",
               "  Precisión: 33 %  (1 de 3 correcto sin ayuda)",
               "  Correcto sin ayuda ......  1  (33%)",
               "  Con ayuda – correcto ....  1  (33%)",
               "  Con ayuda – incorrecto ..  0   (0%)",
               "  Incorrecto, sin ayuda ...  1  (33%)",
               "  Ayudas usadas (1):",
               "    Verbal 1  (1 correcto, 0 incorrectos)",
               "", "ESTUDIANTE: CD", "Objetivo 1: Seguir instrucciones de 2 pasos",
               "  Precisión: 100 %  (1 de 1 correcto sin ayuda)"],
    }[lang]
    lines = text.split("\n")
    assert lines[0] == ("Trial&Tally — Session Summary" if lang == "en" else "Trial&Tally — Resumen de la sesión")
    assert re.match(r"(Date|Fecha): \S", lines[1]) and re.match(r"(Start|Inicio): \d", lines[2])
    assert lines[4:4 + len(expected)] == expected

    # End & Clear: Cancel keeps everything; confirming erases it all.
    page.locator("#demo-clear").click()
    assert page.locator("#demo-confirm").is_visible()
    page.locator("#demo-confirm").get_by_role("button", name=t["cancel"]).click()
    assert not page.locator("#demo-confirm").is_visible()
    expect_state(page, pct(33), counts(lang, 1, 3, 1))
    page.locator("#demo-clear").click()
    page.locator("#demo-confirm").get_by_role("button", name=t["end"]).click()
    expect_state(page, "–", t["none"])
    assert not page.locator("#demo-summary").is_visible()
    page.locator("#demo-tab-1").click()
    expect_state(page, "–", t["none"])
    page.wait_for_function(f"document.querySelector('#demo-live').textContent.includes('{t['cleared']}')")
    assert_clean(page)


@pytest.mark.parametrize("lang", list(LANGS))
def test_demo_summary_with_no_trials(open_page, lang):
    page = open_page(LANGS[lang])
    page.locator("#demo-summary-btn").click()
    assert page.locator("#demo-summary-empty").is_visible()
    assert page.locator("#demo-summary-text").inner_text() == ""


@pytest.mark.parametrize("lang", list(LANGS))
def test_demo_keyboard_only(open_page, lang):
    t = DEMO[lang]
    page = open_page(LANGS[lang], viewport="desktop")
    focused = lambda: page.evaluate("document.activeElement.id || document.activeElement.dataset.record || document.activeElement.dataset.prompt || document.activeElement.dataset.action || document.activeElement.textContent.trim()")  # noqa: E731
    # Tab from the top of the page until the first student tab has focus.
    for _ in range(60):
        page.keyboard.press("Tab")
        if focused() == "demo-tab-0":
            break
    else:
        pytest.fail("couldn't reach the demo with Tab")
    # Arrow keys move between students (and back).
    page.keyboard.press("ArrowRight")
    assert focused() == "demo-tab-1" and page.locator("#demo-tab-1").get_attribute("aria-selected") == "true"
    page.keyboard.press("ArrowLeft")
    assert focused() == "demo-tab-0"

    page.keyboard.press("Tab")
    assert focused() == "correct"
    page.keyboard.press("Enter")
    expect_state(page, t["pct"].format(n=100), counts(lang, 1, 1, 0))

    page.keyboard.press("Tab")
    assert focused() == "prompted"
    page.keyboard.press("Enter")
    assert focused() == "Visual"           # focus moves into the prompt choices
    page.keyboard.press("Tab")
    assert focused() == "Verbal"
    page.keyboard.press("Space")
    assert focused() == "promptedCorrect"  # then to the result buttons
    page.keyboard.press("Tab")
    assert focused() == "promptedIncorrect"
    page.keyboard.press("Enter")
    assert focused() == "prompted"         # and back to Prompted
    expect_state(page, t["pct"].format(n=50), counts(lang, 1, 2, 1))

    page.keyboard.press("Tab")
    assert focused() == "incorrect"
    page.keyboard.press("Enter")
    expect_state(page, t["pct"].format(n=33), counts(lang, 1, 3, 1))

    page.keyboard.press("Tab")
    assert focused() == "demo-summary-btn"
    page.keyboard.press("Enter")
    assert focused() == "demo-summary-title"
    assert "Verbal 1" in page.locator("#demo-summary-text").inner_text()

    page.locator("#demo-undo").focus()
    page.keyboard.press("Enter")
    expect_state(page, t["pct"].format(n=50), counts(lang, 1, 2, 1))

    page.locator("#demo-summary-btn").focus()
    page.keyboard.press("Tab")
    assert focused() == "demo-clear"
    page.keyboard.press("Enter")
    assert page.locator("#demo-confirm").is_visible()
    assert page.evaluate("document.activeElement.value") == "cancel"  # safe choice has focus
    page.keyboard.press("Tab")
    assert page.evaluate("document.activeElement.value") == "clear"
    page.keyboard.press("Enter")
    assert not page.locator("#demo-confirm").is_visible()
    expect_state(page, "–", t["none"])
    assert focused() == "demo-tab-0"

    # Escape closes the dialog without clearing.
    page.keyboard.press("Tab")
    page.keyboard.press("Enter")  # record one Correct
    page.locator("#demo-clear").focus()
    page.keyboard.press("Enter")
    page.keyboard.press("Escape")
    assert not page.locator("#demo-confirm").is_visible()
    assert demo_state(page)[0] == t["pct"].format(n=100)
    assert_clean(page)


# ---------------------------------------------------------------- calculator


@pytest.mark.parametrize("lang", list(LANGS))
def test_calculator(open_page, lang):
    page = open_page(LANGS[lang])
    week, year = page.locator("#calc-week"), page.locator("#calc-year")
    if lang == "en":
        assert week.inner_text() == "50 minutes a week"
        assert year.inner_text() == "30 hours a school year (180 days)"
    else:
        assert week.inner_text() == "50 minutos a la semana"
        assert year.inner_text() == "30 horas por ciclo escolar (180 días)"
    page.get_by_label(re.compile("Group sessions per day|Sesiones grupales por día")).fill("3")
    page.locator("#calc-minutes").fill("1.5")
    expect_week = "22.5 minutes a week" if lang == "en" else "22.5 minutos a la semana"
    expect_year = "13.5 hours a school year (180 days)" if lang == "en" else "13.5 horas por ciclo escolar (180 días)"
    assert week.inner_text() == expect_week and year.inner_text() == expect_year
    page.locator("#calc-sessions").fill("1")
    page.locator("#calc-minutes").fill("0.2")
    assert week.inner_text() == ("1 minute a week" if lang == "en" else "1 minuto a la semana")
    page.locator("#calc-minutes").fill("")
    assert "0" in week.inner_text() and year.inner_text() == ""
    assert page.locator("#calc-output").get_attribute("aria-live") == "polite"
    assert_clean(page)


# ---------------------------------------------------------------- motion and video


@pytest.mark.parametrize("lang", list(LANGS))
def test_reduced_motion_is_static(open_page, lang):
    page = open_page(LANGS[lang], viewport="desktop", reduced_motion="reduce")
    assert page.evaluate("getComputedStyle(document.querySelector('.bar-1')).animationName") == "none"
    assert page.evaluate("getComputedStyle(document.querySelector('.check')).animationName") == "none"
    assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") == "auto"
    story = page.locator("#story")
    assert "is-sticky" not in (story.get_attribute("class") or "")
    shots = page.locator(".story-step .story-shot")
    assert shots.count() == 5
    for i in range(5):
        assert shots.nth(i).is_visible()
    assert not page.locator(".story-phone").is_visible()
    video = page.locator("#preview-video")
    video.scroll_into_view_if_needed()
    page.wait_for_timeout(1500)
    assert page.evaluate("document.querySelector('#preview-video').paused")
    assert video.get_attribute("autoplay") is None
    assert not any(u.endswith(".mp4") for u in page.requests), "video loaded without being played"
    assert_clean(page)


@pytest.mark.parametrize("lang", list(LANGS))
def test_motion_sticky_story_and_video(open_page, lang):
    page = open_page(LANGS[lang], viewport="desktop")
    assert page.evaluate("getComputedStyle(document.querySelector('.bar-1')).animationName") == "bar-rise"
    assert not any(u.endswith(".mp4") for u in page.requests), "video must not load with the page"
    story = page.locator("#story")
    assert "is-sticky" in story.get_attribute("class")
    page.locator('.story-step[data-step="3"]').scroll_into_view_if_needed()
    page.evaluate("document.querySelector('.story-step[data-step=\"3\"]').scrollIntoView({block: 'center'})")
    page.wait_for_timeout(400)
    active = page.evaluate("Array.from(document.querySelectorAll('.stack picture')).findIndex(p => p.classList.contains('is-active'))")
    assert active == 2
    page.locator("#preview-video").scroll_into_view_if_needed()
    page.wait_for_function("!document.querySelector('#preview-video').paused", timeout=5000)
    assert any(u.endswith(f"/assets/video/preview-{lang}.mp4") for u in page.requests)
    assert_clean(page)


def test_phone_story_is_stacked(open_page):
    page = open_page("/", viewport="phone")
    assert "is-sticky" not in (page.locator("#story").get_attribute("class") or "")
    assert page.locator(".story-step .story-shot").nth(0).is_visible()


# ---------------------------------------------------------------- language switch


@pytest.mark.parametrize("start,expected", [
    ("/", "/es/"), ("/es/", "/"), ("/support/", "/es/support/"), ("/es/support/", "/support/"),
    ("/privacy/", "/es/privacy/"), ("/es/privacy/", "/privacy/"), ("/terms/", "/es/terms/"), ("/es/terms/", "/terms/"),
])
def test_language_switch(open_page, start, expected):
    page = open_page(start, viewport="desktop")
    page.locator("nav.lang a").click()
    page.wait_for_load_state()
    assert page.url == page.base + expected
    other = "es" if expected.startswith("/es/") else "en"
    assert page.evaluate("document.documentElement.lang") == other
    # The footer switch goes to the same page.
    page.goto(page.base + start)
    href = page.locator(".footer-links a[hreflang]").get_attribute("href")
    assert href == expected


# ---------------------------------------------------------------- accessibility


@pytest.mark.parametrize("viewport", ["phone", "desktop"])
@pytest.mark.parametrize("path", ALL_PAGES)
def test_axe(open_page, path, viewport):
    page = open_page(path, viewport=viewport)
    scroll_through(page)
    assert run_axe(page) == []


@pytest.mark.parametrize("lang", list(LANGS))
def test_axe_demo_states_and_dark_mode(open_page, lang):
    page = open_page(LANGS[lang], viewport="phone", color_scheme="dark")
    assert run_axe(page) == []
    demo = page.locator("#demo-app")
    demo.locator('[data-step="main"] [data-record="correct"]').click()
    demo.locator('[data-action="prompted"]').click()
    assert run_axe(page, "#demo-app") == []
    demo.locator('[data-prompt="Visual"]').click()
    page.locator("#demo-summary-btn").click()
    assert run_axe(page, "#demo-app") == []
    page.locator("#demo-clear").click()
    assert run_axe(page, "#demo-confirm") == []


@pytest.mark.parametrize("lang", list(LANGS))
def test_live_region_and_names(open_page, lang):
    page = open_page(LANGS[lang])
    live = page.locator("#demo-live")
    assert live.get_attribute("aria-live") == "polite"
    assert page.locator("#preview-video").get_attribute("aria-label")
    # The phone screenshots carry descriptive alt text; decorative copies are hidden.
    alts = page.locator(".story-step img").evaluate_all("els => els.map(e => e.alt)")
    assert len(alts) == 5 and all(len(a) > 30 for a in alts)
    assert page.locator(".story-phone").get_attribute("aria-hidden") == "true"
    assert external_requests(page) == []
