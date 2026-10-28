# Decisions

Judgment calls made while building the site. Items marked **(review)** are ones Gabe or Laurel may
want to revisit. Paths are relative to `/Users/laurelhamby/Developer/trialandtally-site`.

## Website redesign (2026-10-28, branch `redesign`)

### Build and structure
- **Generated pages.** Every page is built by `_tools/build.py` (Python standard library, so it
  runs with the Mac's `python3`) from `_src/`: one home template with English/Spanish string
  files, and the Support/Privacy/Terms/404 content copied verbatim from the old pages. The output
  is committed, so GitHub Pages serves plain files as before (Jekyll still runs, `_config.yml`
  excludes the notes). `check_site.py` fails if the pages are out of date with `_src/`.
- **URLs unchanged:** `/`, `/support/`, `/privacy/`, `/terms/`, the `/es/` versions, `404.html`,
  `CNAME`, and the root icons (`favicon-32.png`, `apple-touch-icon.png`, `app-icon.png`).
  `styles.css` was replaced by `assets/site.css` (not a page URL).
- **Support, Privacy and Terms content is unchanged**; only the header, footer and styles around
  it changed. `test_static.py` compares each page's text with commit `71bd51f` (last `main`).
- **Absolute own-domain URLs** (`https://trialandtally.com/...`) are used only where they must be:
  canonical, hreflang, `og:url`, `og:image`. Everything the browser loads is a relative path.
- `<meta name="referrer" content="no-referrer">` on every page (nothing leaks to apps.apple.com
  later). No CSP header is possible on GitHub Pages; the checker forbids inline scripts instead,
  so one could be added later.

### Libraries, fonts, motion
- **No GSAP.** The sticky "How it works" phone uses IntersectionObserver (about 30 lines). That
  saves ~70 KB of script and a license file, and nothing is lost: it only swaps which screenshot
  is showing. **No web font**: the system font stack (San Francisco on Apple devices, Roboto on
  Chromebooks) looks right and costs nothing.
- **Hero icon animation.** The real icon with the bars and check painted out
  (`assets/img/icon-base-*.webp`, made by `_tools/make_assets.py`), with the red/yellow/green bars
  and the check redrawn on top in SVG at the measured positions (the check path was fitted to the
  original to within a few pixels). Bars rise, then the check draws itself (CSS only). Under
  reduced motion the final icon shows with no animation.
- **Reduced motion everywhere:** no hero animation, no smooth scrolling, the story is the stacked
  list (screenshot + caption), and the video never starts by itself.
- **The active "How it works" step is marked with a blue bar and a filled number**, not by fading
  the other steps: faded text failed the 4.5:1 contrast check.
- **Dark mode** is supported (the old site had it). The demo uses the app's dark grouped
  background. Outcome button colors stay the light-mode values in both modes so white/black text
  keeps 4.5:1+.

### App Store badge
- **Apple's official badges**, downloaded unmodified from Apple's marketing tools (black; English
  US and Spanish Mexico "Descárgalo en el App Store") into `assets/img/badges/`. A test checks
  they're byte-for-byte unchanged.
- **(review) "Coming soon to the App Store" is a plain black text pill, not Apple's badge
  artwork.** Apple's guidelines say the badge should link to the app's App Store page; an
  unlinked badge would look like a broken button. The real badge (at 50 px tall, with clear space)
  appears automatically once `appStoreURL` is set in `_src/config.json`
  (`python3 _tools/set_app_store_url.py <url>`). Both modes are tested.

### Copy
- **(review) Demo note:** the brief suggested "Nothing you tap here is saved. The app works the
  same way." The app does keep the session on the device until End & Clear (it survives closing
  and restarts), so to keep the copy accurate it says: "Nothing you tap here is saved or sent
  anywhere. In the app, a session stays only on your device until you tap End & Clear."
- **Hero subhead:** "...then clear it all. No accounts, no cloud, nothing kept." rather than
  "nothing stored", for the same reason.
- **(review) Privacy bullet 5** is "Nothing for your district to vet on our side: no sign-up, no
  servers, no student records with us. When you share a summary, follow your district's rules."
  It avoids promising that no district approval is needed, which only a district can say.
- **(review) Time calculator:** defaults are 5 group sessions a day and 2 minutes each (50
  minutes a week, 30 hours a year), a 5-day week and a 180-day year; results to one decimal. It
  is headed "Your estimate" and says it's based only on what the visitor enters.
- **(review) "Who it's for" one-liners** (e.g. "Discrete trials with the prompt level for each
  one" for ABA therapists) are mine; the list itself is from the requirements.
- **"Made by a school SLP"** (Spanish "Creada por una terapeuta de lenguaje escolar", the wording
  already approved for the app preview video). Says the app was built with a practicing school
  SLP and shaped by testing in real sessions (Laurel's 2026-10-20 session). No name or photo.
- **FAQ** on the home page: subscription?, trial end, internet, customizing prompts/labels,
  students/goals limits; everything else links to Support.
- No testimonials, ratings, user counts or time-saved figures of our own (a test checks the copy
  for the obvious ones).
- **Spanish** follows the app's Mexican wording: Con ayuda, Terminar y borrar, hoja de registro,
  Configuración, Compartir en familia, agregar, tú. "$4.99 un solo pago" for "$4.99 once".
  **(review)** by a native speaker.

### The live demo (`assets/js/demo-core.js`, `assets/js/site.js`)
- **Scoring is a line-for-line port of the app** (`GoalStats`, `Percent.of`, `SessionSummary`
  plain text, `CountText`): only correct on own counts, whole-number percent with integer
  half-up rounding, the same dotted column layout, Spanish plural forms ("1 de 10 correcto sin
  ayuda", "(1 correcto, 0 incorrectos)"). 36 unit tests use cases from the app's ScoringTests and
  SummaryTests (the REQUIREMENTS sample, the rounding table, the 600-trial case).
- **Summary format = the app's plain-text export**: "(65%)" rows in both languages (the export
  doesn't localize them), while the goal card shows "65 %" in Spanish like the app's screen.
  Dates/times use the browser's en-US / es-MX formats, which match the app ("Tue, Oct 20, 2026",
  "mar, 20 de oct de 2026", "2:00 p.m."). The demo has a start time (page load), no end time,
  no notes.
- Two students (AB, CD) with one goal each, as the brief allowed; per-student Undo; students are
  a proper tab list (arrow keys, Home/End).
- **End & Clear asks "Are you sure?"** in a native `<dialog>` (Cancel focused), like the app.
- **Focus** moves into the prompt choices after Prompted, to the result buttons after picking a
  prompt, and back to Prompted after recording; every tap is announced in a polite live region
  ("Verbal prompt, correct. AB: 50 percent, 1 of 2 correct on own · 1 prompted").
- The counts line wraps as two phrases, like the app's `WrappingPhrases`.
- The summary text scrolls sideways inside its own box when a Spanish line is wider than a small
  phone (the page itself never scrolls sideways; tested at 320 px).

### Images, video, weight
- **Screenshots:** the plain App Store iPhone 6.9" set; 5 of the 7 are used (04 add student,
  01 session, 02 prompt, 03 summary, 05 clear); 06 share and 07 settings aren't needed. AVIF and
  WebP at 300/600/900 px wide with a 600 px JPG fallback, lazy except the hero.
- **(review) Preview video:** H.264 MP4 only, 590x1280, CRF 20, no audio track (it's silent),
  tagged BT.709 so the green matches the app (the source is BT.709 but untagged, which made
  browsers show a brighter green). 1.25 MB English, 1.40 MB Spanish. A VP9 WebM came out larger,
  so there's none. `preload="none"`; it starts muted when half of it scrolls into view and pauses
  when it leaves (never under reduced motion, and never again after the viewer pauses it). Poster
  is the "One tap per trial" frame (the App Store poster time), WebP only.
- **Share images** (`assets/img/share-en.png`, `share-es.png`, 1200x630 PNG): icon, name,
  headline, one line, price line, and the session screenshot in a phone; drawn from HTML by
  `_tools/make_share_images.py`. The Spanish price line was shortened to "7 días gratis · $4.99
  un solo pago · Nada se guarda" to fit on one line.
- **Weight:** the home page transfers 132–160 KB on first view and 184–369 KB after scrolling the
  whole page (every lazy image; 3x phone is the worst case), before the video, measured in Chrome
  against the local server without gzip. GitHub Pages gzips HTML/CSS/JS, so real numbers are a
  little lower.

### Tests and tools
- Browser tests use the Mac's **Google Chrome** headless through Playwright (Python), one
  browser for the whole run. Dev tools live in a git-ignored `.venv/`; axe-core 4.14.0 is
  downloaded (checksum-verified) into the git-ignored `_tools/.cache/` by `_tools/setup_dev.sh`.
- **Lighthouse** was run once with a temporary Node.js in Claude's scratch folder (not part of the
  repo): mobile English 100/100/100/100, Spanish 99/100/100/100 (Performance / Accessibility /
  Best Practices / SEO). The remaining hints were server-side (gzip, cache lifetimes).
- Review screenshots of the full page are stitched from screen-sized captures: Chrome can't
  capture more than ~16,000 px at once, and the sticky phone needs a real screen height.
