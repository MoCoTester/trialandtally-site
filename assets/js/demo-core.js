// Trial&Tally demo scoring and summary text. A line-for-line port of the app's
// Models/GoalStats.swift (Percent, GoalStats), Models/SessionSummary.swift (plain text) and
// Utilities/CountText.swift (English and Mexican Spanish wording). Pure functions, no DOM,
// no storage. Tested by _tools/tests/test_demo_core.py against cases from the app's tests.

export const KINDS = ["correct", "promptedCorrect", "promptedIncorrect", "incorrect"];

/** Whole-number percent, rounded half up (2 of 3 -> 67, 1 of 8 -> 13). Null with no trials. */
export function percent(part, total) {
  if (!(total > 0) || part < 0) return null;
  // Integer math like the app, so exact halves never round the wrong way.
  return Math.floor((part * 200 + total) / (2 * total));
}

/**
 * Counts for one goal. trials: [{kind, prompt}] where kind is one of KINDS and prompt is the
 * prompt type's name (prompted trials only). promptOrder: prompt names in Settings order.
 */
export function goalStats(trials, promptOrder = []) {
  const s = { correct: 0, promptedCorrect: 0, promptedIncorrect: 0, incorrect: 0 };
  const tallies = new Map();
  for (const t of trials) {
    s[t.kind] += 1;
    if ((t.kind === "promptedCorrect" || t.kind === "promptedIncorrect") && t.prompt) {
      if (!tallies.has(t.prompt)) tallies.set(t.prompt, { name: t.prompt, correct: 0, incorrect: 0 });
      tallies.get(t.prompt)[t.kind === "promptedCorrect" ? "correct" : "incorrect"] += 1;
    }
  }
  // Settings order first, then any others in the order they were first used.
  const prompts = [];
  for (const name of promptOrder) {
    if (tallies.has(name)) { prompts.push(tallies.get(name)); tallies.delete(name); }
  }
  prompts.push(...tallies.values());
  for (const p of prompts) p.total = p.correct + p.incorrect;
  const total = s.correct + s.promptedCorrect + s.promptedIncorrect + s.incorrect;
  return {
    counts: s,
    total,
    correctOnOwn: s.correct,
    promptedTotal: s.promptedCorrect + s.promptedIncorrect,
    accuracy: percent(s.correct, total),
    percentOf: (kind) => percent(s[kind], total),
    prompts,
  };
}

// Spanish plural: "one" only for exactly 1 (as in the app's String Catalog).
const es1 = (n, one, other) => (n === 1 ? one : other);

export const TEXT = {
  en: {
    prompts: ["Visual", "Verbal", "Physical"],
    title: "Trial&Tally — Session Summary",
    date: (d) => `Date: ${d}`,
    start: (t) => `Start: ${t}`,
    student: (i) => `STUDENT: ${i}`,
    goal: (n, label) => (label.trim() ? `Goal ${n}: ${label}` : `Goal ${n}`),
    noTrials: "No trials recorded.",
    noTrialsYet: "No trials yet",
    cardPercent: (p) => `${p}%`,
    accuracyLine: (p, c, t) => `Accuracy: ${p}%  (${c} of ${t} correct on own)`,
    correctOnOwn: (c, t) => `${c} of ${t} correct on own`,
    prompted: (n) => `${n} prompted`,
    rows: ["Correct on own", "Prompted – correct", "Prompted – incorrect", "Incorrect, no prompt"],
    promptsUsed: (n) => `Prompts used (${n}):`,
    correctIncorrect: (c, i) => `(${c} correct, ${i} incorrect)`,
    locale: "en-US",
  },
  es: {
    prompts: ["Visual", "Verbal", "Física"],
    title: "Trial&Tally — Resumen de la sesión",
    date: (d) => `Fecha: ${d}`,
    start: (t) => `Inicio: ${t}`,
    student: (i) => `ESTUDIANTE: ${i}`,
    goal: (n, label) => (label.trim() ? `Objetivo ${n}: ${label}` : `Objetivo ${n}`),
    noTrials: "No se registraron ensayos.",
    noTrialsYet: "Aún no hay ensayos",
    // The goal card localizes "%lld%%" as "70 %"; the plain-text export keeps "(70%)" like the app.
    cardPercent: (p) => `${p} %`,
    accuracyLine: (p, c, t) =>
      `Precisión: ${p} %  (${c} de ${t} ${es1(c, "correcto sin ayuda", "correctos sin ayuda")})`,
    correctOnOwn: (c, t) => `${c} de ${t} ${es1(c, "correcto sin ayuda", "correctos sin ayuda")}`,
    prompted: (n) => `${n} con ayuda`,
    rows: ["Correcto sin ayuda", "Con ayuda – correcto", "Con ayuda – incorrecto", "Incorrecto, sin ayuda"],
    promptsUsed: (n) => `Ayudas usadas (${n}):`,
    correctIncorrect: (c, i) =>
      `(${c} ${es1(c, "correcto", "correctos")}, ${i} ${es1(i, "incorrecto", "incorrectos")})`,
    locale: "es-MX",
  },
};

/** Character count like Swift's String.count (user-perceived characters, close enough here). */
const len = (str) => Array.from(str).length;
const padLeft = (text, width) => " ".repeat(Math.max(0, width - len(text))) + text;
const padRight = (text, width) => text + " ".repeat(Math.max(0, width - len(text)));

/** "7 of 10 correct on own · 2 prompted", or "No trials yet". */
export function countsLine(stats, lang) {
  const t = TEXT[lang];
  if (stats.total === 0) return t.noTrialsYet;
  return `${t.correctOnOwn(stats.correctOnOwn, stats.total)} · ${t.prompted(stats.promptedTotal)}`;
}

/** The lines for one goal, laid out exactly like SessionSummary.goalLines. */
export function goalLines(number, label, stats, lang) {
  const t = TEXT[lang];
  const lines = [t.goal(number, label), "  " + t.accuracyLine(stats.accuracy ?? 0, stats.correctOnOwn, stats.total)];
  const labelWidth = Math.max(...t.rows.map(len)) + 3;
  const countWidth = Math.max(2, String(stats.total).length);
  const percents = KINDS.map((k) => `(${stats.percentOf(k) ?? 0}%)`);
  const percentWidth = Math.max(5, ...percents.map(len));
  t.rows.forEach((row, i) => {
    const dots = ".".repeat(Math.max(2, labelWidth - len(row) - 1));
    lines.push(`  ${row} ${dots} ${padLeft(String(stats.counts[KINDS[i]]), countWidth)}  ${padLeft(percents[i], percentWidth)}`);
  });
  if (stats.promptedTotal > 0) {
    lines.push("  " + t.promptsUsed(stats.promptedTotal));
    const nameWidth = Math.max(0, ...stats.prompts.map((p) => len(p.name))) + 1;
    const countW = String(Math.max(0, ...stats.prompts.map((p) => p.total))).length;
    for (const p of stats.prompts) {
      lines.push(`    ${padRight(p.name, nameWidth)}${padLeft(String(p.total), countW)}  ${t.correctIncorrect(p.correct, p.incorrect)}`);
    }
  }
  return lines;
}

export function dateString(date, lang) {
  return new Intl.DateTimeFormat(TEXT[lang].locale, { weekday: "short", month: "short", day: "numeric", year: "numeric" })
    .format(date);
}

export function timeString(date, lang) {
  // Plain spaces (Intl puts a narrow no-break space before AM/PM), so a pasted copy reads cleanly.
  return new Intl.DateTimeFormat(TEXT[lang].locale, { hour: "numeric", minute: "2-digit" })
    .format(date).replace(/[  ]/g, " ");
}

/**
 * Plain-text summary like SessionSummary.plainText(). session: {date, start (Date or null),
 * students: [{initials, notes, goals: [{label, trials}]}]}. Goals with zero trials are left off;
 * a student with none says "No trials recorded."
 */
export function summaryText(session, lang) {
  const t = TEXT[lang];
  const lines = [t.title, t.date(dateString(session.date, lang))];
  if (session.start) lines.push(t.start(timeString(session.start, lang)));
  for (const student of session.students) {
    lines.push("", t.student(student.initials));
    const goals = student.goals
      .map((g, i) => ({ number: i + 1, label: g.label, stats: goalStats(g.trials, t.prompts) }))
      .filter((g) => g.stats.total > 0);
    if (goals.length === 0) lines.push(t.noTrials);
    goals.forEach((g, i) => {
      if (i > 0) lines.push("");
      lines.push(...goalLines(g.number, g.label, g.stats, lang));
    });
    if (student.notes && student.notes.trim()) lines.push(`${lang === "es" ? "Notas" : "Notes"}: ${student.notes.trim()}`);
  }
  return lines.join("\n");
}

/** Time-saved calculator: minutes per week (5 school days) and hours per 180-day school year. */
export function timeSaved(sessionsPerDay, minutesPerSession) {
  const s = Number(sessionsPerDay), m = Number(minutesPerSession);
  if (!Number.isFinite(s) || !Number.isFinite(m) || s < 0 || m < 0) return null;
  const perDay = s * m;
  return { minutesPerWeek: perDay * 5, hoursPerYear: (perDay * 180) / 60 };
}
