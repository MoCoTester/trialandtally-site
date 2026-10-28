// Trial&Tally home page: the live demo, the time calculator, the sticky "How it works" phone
// and the lazy preview video. No storage, no cookies, no network requests of its own.
import { goalStats, countsLine, summaryText, timeSaved, TEXT } from "./demo-core.js";

const lang = document.documentElement.lang === "es" ? "es" : "en";
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const data = JSON.parse($("#demo-data")?.textContent || "{}");

// ---------------------------------------------------------------- demo

function initDemo() {
  const app = $("#demo-app");
  if (!app) return;
  const t = TEXT[lang];
  const el = {
    tabs: $$(".demo-tab", app),
    panel: $("#demo-panel"),
    title: $("#demo-goal-title"),
    counts: $("#demo-counts"),
    pct: $("#demo-pct"),
    steps: $$(".goal-step", app),
    chosen: $("#demo-chosen"),
    undo: $("#demo-undo"),
    summaryButton: $("#demo-summary-btn"),
    summary: $("#demo-summary"),
    summaryTitle: $("#demo-summary-title"),
    summaryText: $("#demo-summary-text"),
    summaryEmpty: $("#demo-summary-empty"),
    clear: $("#demo-clear"),
    dialog: $("#demo-confirm"),
    live: $("#demo-live"),
  };

  let session, current, step, chosenPrompt, summaryOpen = false;
  function reset() {
    session = {
      date: new Date(),
      start: new Date(),
      students: data.initials.map((initials, i) => ({ initials, notes: "", goals: [{ label: data.goals[i], trials: [] }] })),
    };
    current = 0;
    step = "main";
    chosenPrompt = null;
  }

  const goal = () => session.students[current].goals[0];
  const stats = () => goalStats(goal().trials, t.prompts);

  function announce(text) {
    // Clear first so the same message twice in a row is still read.
    el.live.textContent = "";
    window.setTimeout(() => { el.live.textContent = text; }, 30);
  }

  function statusText() {
    const s = stats();
    const pct = s.accuracy === null ? "" : data.pct.replace("{pct}", s.accuracy) + ", ";
    return `${session.students[current].initials}: ${pct}${countsLine(s, lang)}`;
  }

  function render() {
    const s = stats();
    el.title.textContent = goal().label;
    // Two phrases that wrap as units, like the app ("7 of 10 correct on own ·" / "2 prompted").
    const [first, second] = countsLine(s, lang).split(" · ");
    el.counts.replaceChildren(phrase(second === undefined ? first : `${first} ·`));
    if (second !== undefined) el.counts.append(" ", phrase(second));
    el.pct.innerHTML = "";
    el.pct.classList.toggle("is-empty", s.accuracy === null);
    const pct = document.createElement("span");
    pct.setAttribute("aria-hidden", "true");
    pct.textContent = s.accuracy === null ? "–" : t.cardPercent(s.accuracy);
    el.pct.append(pct);
    if (s.accuracy !== null) {
      const sr = document.createElement("span");
      sr.className = "sr-only";
      sr.textContent = data.pct.replace("{pct}", s.accuracy);
      el.pct.append(sr);
    }
    el.tabs.forEach((tab, i) => {
      const selected = i === current;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    });
    el.panel.setAttribute("aria-labelledby", el.tabs[current].id);
    el.steps.forEach((node) => { node.hidden = node.dataset.step !== step; });
    if (chosenPrompt) el.chosen.textContent = chosenPrompt;
    el.undo.disabled = goal().trials.length === 0;
    renderSummary();
  }

  function renderSummary() {
    el.summary.hidden = !summaryOpen;
    el.summaryButton.setAttribute("aria-expanded", String(summaryOpen));
    el.summaryButton.textContent = summaryOpen ? data.hideSummary : data.seeSummary;
    if (!summaryOpen) return;
    const any = session.students.some((st) => st.goals.some((g) => g.trials.length));
    el.summaryEmpty.hidden = any;
    el.summaryText.textContent = any ? summaryText(session, lang) : "";
  }

  function phrase(text) {
    const span = document.createElement("span");
    span.className = "phrase";
    span.textContent = text;
    return span;
  }

  function setStep(next, focusSel) {
    step = next;
    render();
    if (focusSel) $(focusSel, app)?.focus();
  }

  function record(kind) {
    const prompted = kind === "promptedCorrect" || kind === "promptedIncorrect";
    goal().trials.push(prompted ? { kind, prompt: chosenPrompt } : { kind });
    const said = data.recorded[kind].replace("{prompt}", chosenPrompt || "");
    if (prompted) {
      step = "main";
      chosenPrompt = null;
    }
    render();
    if (prompted) $('[data-step="main"] [data-action="prompted"]', app).focus();
    announce(`${said}. ${statusText()}`);
  }

  app.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || !app.contains(button)) return;
    if (button.dataset.record) return record(button.dataset.record);
    if (button.dataset.prompt) {
      chosenPrompt = button.dataset.prompt;
      return setStep("result", '[data-step="result"] [data-record="promptedCorrect"]');
    }
    switch (button.dataset.action) {
      case "prompted": return setStep("choose", '[data-step="choose"] [data-prompt]');
      case "cancel": chosenPrompt = null; return setStep("main", '[data-step="main"] [data-action="prompted"]');
      case "change": return setStep("choose", '[data-step="choose"] [data-prompt]');
      case "summary": return toggleSummary();
    }
  });

  function toggleSummary() {
    summaryOpen = !summaryOpen;
    render();
    if (summaryOpen) el.summaryTitle.focus();
  }

  el.undo.addEventListener("click", () => {
    if (!goal().trials.length) return announce(data.nothingToUndo);
    goal().trials.pop();
    render();
    announce(`${data.undo}. ${statusText()}`);
    if (el.undo.disabled) el.tabs[current].focus();
  });

  // Students: a tab list with arrow-key, Home and End support.
  el.tabs.forEach((tab, i) => {
    tab.addEventListener("click", () => selectStudent(i));
    tab.addEventListener("keydown", (event) => {
      const n = el.tabs.length;
      const next = { ArrowRight: (i + 1) % n, ArrowLeft: (i - 1 + n) % n, Home: 0, End: n - 1 }[event.key];
      if (next === undefined) return;
      event.preventDefault();
      selectStudent(next);
      el.tabs[next].focus();
    });
  });
  function selectStudent(i) {
    current = i;
    step = "main";
    chosenPrompt = null;
    render();
  }

  // End & Clear: "Are you sure?" first, like the app.
  el.clear.addEventListener("click", () => {
    if (typeof el.dialog.showModal === "function") el.dialog.showModal();
    else if (window.confirm($("#demo-confirm-title").textContent)) clearAll();
  });
  el.dialog.addEventListener("close", () => {
    if (el.dialog.returnValue === "clear") clearAll();
    else el.clear.focus();
    el.dialog.returnValue = "";
  });
  function clearAll() {
    reset();
    summaryOpen = false;
    render();
    el.tabs[0].focus();
    announce(data.cleared);
  }

  reset();
  render();
  app.dataset.ready = "true";
}

// ---------------------------------------------------------------- calculator

function initCalculator() {
  const sessions = $("#calc-sessions");
  const minutes = $("#calc-minutes");
  if (!sessions || !minutes) return;
  const c = data.calc;
  const fmt = new Intl.NumberFormat(TEXT[lang].locale, { maximumFractionDigits: 1 });
  const word = (n, one, other) => (n === 1 ? one : other);
  function update() {
    const blank = sessions.value.trim() === "" || minutes.value.trim() === "";
    const result = blank ? null : timeSaved(sessions.value, minutes.value);
    const week = $("#calc-week"), year = $("#calc-year");
    if (!result) {
      week.textContent = c.invalid;
      year.textContent = "";
      return;
    }
    const w = Math.round(result.minutesPerWeek * 10) / 10;
    const h = Math.round(result.hoursPerYear * 10) / 10;
    week.textContent = c.week.replace("{n}", fmt.format(w)).replace("{minutes}", word(w, c.minute_one, c.minute_other));
    year.textContent = c.year.replace("{n}", fmt.format(h)).replace("{hours}", word(h, c.hour_one, c.hour_other));
  }
  sessions.addEventListener("input", update);
  minutes.addEventListener("input", update);
  update();
}

// ---------------------------------------------------------------- "How it works" sticky phone

function initStory() {
  const story = $("#story");
  if (!story || !("IntersectionObserver" in window)) return;
  const wide = window.matchMedia("(min-width: 900px)");
  const steps = $$(".story-step", story);
  const shots = $$(".story-phone .stack picture", story);
  let observer = null;

  function activate(index) {
    steps.forEach((s, i) => s.classList.toggle("is-active", i === index));
    shots.forEach((s, i) => s.classList.toggle("is-active", i === index));
  }

  function apply() {
    const sticky = wide.matches && !reducedMotion.matches;
    story.classList.toggle("is-sticky", sticky);
    if (observer) { observer.disconnect(); observer = null; }
    if (!sticky) return;
    activate(0);
    observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) activate(steps.indexOf(entry.target));
      }
    }, { rootMargin: "-45% 0px -45% 0px" });
    steps.forEach((s) => observer.observe(s));
  }
  wide.addEventListener?.("change", apply);
  reducedMotion.addEventListener?.("change", apply);
  apply();
}

// ---------------------------------------------------------------- preview video

function initVideo() {
  const video = $("#preview-video");
  if (!video || !("IntersectionObserver" in window)) return;
  // preload="none" keeps it out of the page load. It starts (muted) when scrolled into view,
  // except under reduced motion, where it waits for the play button.
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (reducedMotion.matches) return;
      if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
        if (video.paused && !video.dataset.userPaused) video.play().catch(() => {});
      } else if (!video.paused) {
        video.dataset.autoPaused = "true";
        video.pause();
      }
    }
  }, { threshold: [0, 0.5] });
  video.addEventListener("pause", () => {
    // Remember a pause the viewer chose, so scrolling back doesn't restart it.
    if (!video.dataset.autoPaused && !video.ended) video.dataset.userPaused = "true";
    delete video.dataset.autoPaused;
  });
  video.addEventListener("play", () => { delete video.dataset.userPaused; });
  observer.observe(video);
}

initDemo();
initCalculator();
initStory();
initVideo();
