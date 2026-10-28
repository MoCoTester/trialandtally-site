"""Unit tests for assets/js/demo-core.js (the demo's scoring and summary text), run in headless
Chrome. Expected values come from the app's own tests:
TrialAndTallyTests/ScoringTests.swift and SummaryTests.swift (sample from REQUIREMENTS.md,
rounding table, 600-trial case, plain-text layout) and the Spanish String Catalog wording."""
import pytest

pytestmark = pytest.mark.usefixtures("base_url")


@pytest.fixture(scope="module")
def js(browser, base_url):
    context = browser.new_context()
    page = context.new_page()
    page.goto(base_url + "/404.html")

    def run(body, arg=None):
        return page.evaluate(
            "async ([body, arg]) => { const m = await import('/assets/js/demo-core.js');"
            " return (new Function('m', 'arg', body))(m, arg); }", [body, arg])
    yield run
    context.close()


def trials(spec):
    """'13c 2pc:Visual 1pi:Visual 1i' -> list of trial dicts."""
    out = []
    kinds = {"c": "correct", "pc": "promptedCorrect", "pi": "promptedIncorrect", "i": "incorrect"}
    for part in spec.split():
        count, rest = int("".join(ch for ch in part if ch.isdigit())), part.lstrip("0123456789")
        kind, _, prompt = rest.partition(":")
        out += [{"kind": kinds[kind], **({"prompt": prompt} if prompt else {})}] * count
    return out


SAMPLE = trials("13c 2pc:Visual 1pi:Visual 2pc:Verbal 1pi:Physical 1i")


@pytest.mark.parametrize("part,total,expected", [
    (0, 1, 0), (1, 1, 100), (1, 3, 33), (2, 3, 67), (1, 8, 13), (1, 200, 1), (1, 201, 0),
    (5, 8, 63), (1, 6, 17), (7, 7, 100), (333, 600, 56), (67, 600, 11), (50, 600, 8),
])
def test_whole_number_rounding_half_up(js, part, total, expected):
    assert js("return m.percent(arg[0], arg[1])", [part, total]) == expected


def test_percent_of_zero_total_is_null(js):
    assert js("return m.percent(0, 0)") is None


def test_only_correct_on_own_counts(js):
    s = js("const s = m.goalStats(arg); return [s.total, s.correctOnOwn, s.accuracy]", trials("1c 1pc:Visual 1pi:Visual 1i"))
    assert s == [4, 1, 25]


def test_sample_from_requirements(js):
    s = js("""const s = m.goalStats(arg, m.TEXT.en.prompts);
              return {total: s.total, acc: s.accuracy, pcts: m.KINDS.map(s.percentOf), prompted: s.promptedTotal,
                      prompts: s.prompts.map(p => [p.name, p.correct, p.incorrect])}""", SAMPLE)
    assert s == {"total": 20, "acc": 65, "pcts": [65, 20, 10, 5], "prompted": 6,
                 "prompts": [["Visual", 2, 1], ["Verbal", 2, 0], ["Physical", 0, 1]]}


def test_prompts_ordered_by_settings_then_first_use(js):
    names = js("return m.goalStats(arg, m.TEXT.en.prompts).prompts.map(p => p.name)",
               trials("1pc:Gestural 1pi:Verbal"))
    assert names == ["Verbal", "Gestural"]


def session(goals, notes="", initials="AB", more=None):
    return {"initials": initials, "notes": notes, "goals": goals, **(more or {})}


def summary(js, students, lang="en"):
    return js("""return m.summaryText({date: new Date(2026, 9, 20, 14, 0), start: new Date(2026, 9, 20, 14, 0),
                                       students: arg[0]}, arg[1])""", [students, lang])


def test_plain_text_matches_requirements_sample(js):
    text = summary(js, [session([{"label": "/r/ initial – words", "trials": SAMPLE},
                                 {"label": "Unused goal", "trials": []}],
                                notes="Needed a movement break midway.")])
    # The app's SummaryTests.plainTextMatchesRequirementsSample (the demo has no end time).
    assert text == "\n".join([
        "Trial&Tally — Session Summary",
        "Date: Tue, Oct 20, 2026",
        "Start: 2:00 PM",
        "",
        "STUDENT: AB",
        "Goal 1: /r/ initial – words",
        "  Accuracy: 65%  (13 of 20 correct on own)",
        "  Correct on own ........ 13  (65%)",
        "  Prompted – correct ....  4  (20%)",
        "  Prompted – incorrect ..  2  (10%)",
        "  Incorrect, no prompt ..  1   (5%)",
        "  Prompts used (6):",
        "    Visual   3  (2 correct, 1 incorrect)",
        "    Verbal   2  (2 correct, 0 incorrect)",
        "    Physical 1  (0 correct, 1 incorrect)",
        "Notes: Needed a movement break midway.",
    ])


def test_no_prompt_section_without_prompts(js):
    text = summary(js, [session([{"label": "G", "trials": trials("1c")}], initials="CD")])
    assert "Prompts used" not in text
    assert "  Correct on own ........  1  (100%)" in text


def test_student_with_no_trials_says_so(js):
    text = summary(js, [session([{"label": "G", "trials": trials("1c")}]),
                        session([{"label": "Other", "trials": []}], initials="CD")])
    assert text.endswith("STUDENT: CD\nNo trials recorded.")


def test_unnamed_goals_and_zero_trial_goals(js):
    text = summary(js, [session([{"label": "", "trials": trials("1c")}, {"label": "Turn taking", "trials": trials("1c")},
                                 {"label": "", "trials": []}])])
    assert "\nGoal 1\n" in text and "\nGoal 2: Turn taking\n" in text
    assert "Goal 1:" not in text and "Goal 3" not in text


def test_six_hundred_trials(js):
    # The app's LargeCountTests.fiveHundredTrialsOnOneGoal.
    text = summary(js, [session([{"label": "G", "trials": trials("333c 150pc:Visual 67pi:Visual 50i")}])])
    assert "Accuracy: 56%  (333 of 600 correct on own)" in text
    assert "Correct on own ........ 333  (56%)" in text
    assert "Incorrect, no prompt ..  50   (8%)" in text
    assert "Prompts used (217):" in text


def test_spanish_wording_and_plurals(js):
    text = summary(js, [session([{"label": "/r/ inicial – palabras", "trials": trials("13c 2pc:Visual 1pi:Visual 2pc:Verbal 1pi:Física 1i")}],
                                notes="Necesitó una pausa.")], "es")
    lines = text.split("\n")
    assert lines[0] == "Trial&Tally — Resumen de la sesión"
    assert lines[1] == "Fecha: mar, 20 de oct de 2026"
    assert lines[2] == "Inicio: 2:00 p.m."
    assert lines[4:] == [
        "ESTUDIANTE: AB",
        "Objetivo 1: /r/ inicial – palabras",
        "  Precisión: 65 %  (13 de 20 correctos sin ayuda)",
        "  Correcto sin ayuda ...... 13  (65%)",
        "  Con ayuda – correcto ....  4  (20%)",
        "  Con ayuda – incorrecto ..  2  (10%)",
        "  Incorrecto, sin ayuda ...  1   (5%)",
        "  Ayudas usadas (6):",
        "    Visual 3  (2 correctos, 1 incorrecto)",
        "    Verbal 2  (2 correctos, 0 incorrectos)",
        "    Física 1  (0 correctos, 1 incorrecto)",
        "Notas: Necesitó una pausa.",
    ]


def test_spanish_singular_correct(js):
    text = summary(js, [session([{"label": "", "trials": trials("1c 9i")}])], "es")
    assert "Precisión: 10 %  (1 de 10 correcto sin ayuda)" in text
    assert "\nObjetivo 1\n" in text


@pytest.mark.parametrize("lang,spec,expected", [
    ("en", "", "No trials yet"),
    ("en", "7c 2pc:Visual 1i", "7 of 10 correct on own · 2 prompted"),
    ("en", "1c", "1 of 1 correct on own · 0 prompted"),
    ("es", "", "Aún no hay ensayos"),
    ("es", "7c 2pc:Visual 1i", "7 de 10 correctos sin ayuda · 2 con ayuda"),
    ("es", "1c 1i", "1 de 2 correcto sin ayuda · 0 con ayuda"),
])
def test_goal_card_counts_line(js, lang, spec, expected):
    assert js("return m.countsLine(m.goalStats(arg[0]), arg[1])", [trials(spec) if spec else [], lang]) == expected


def test_card_percent_format(js):
    assert js("return [m.TEXT.en.cardPercent(70), m.TEXT.es.cardPercent(70)]") == ["70%", "70 %"]


@pytest.mark.parametrize("sessions,minutes,week,year", [
    (5, 2, 50, 30), (3, 1.5, 22.5, 13.5), (0, 2, 0, 0), (8, 3, 120, 72),
])
def test_time_saved(js, sessions, minutes, week, year):
    r = js("return m.timeSaved(arg[0], arg[1])", [sessions, minutes])
    assert r == {"minutesPerWeek": week, "hoursPerYear": year}


def test_time_saved_rejects_bad_input(js):
    assert js("return [m.timeSaved(-1, 2), m.timeSaved('x', 2), m.timeSaved(2, -1)]") == [None, None, None]
