# trialandtally.com

Static site for the Trial&Tally iPhone/iPad app: a one-page product site (English `/`, Spanish
`/es/`) plus Support, Privacy and Terms in both languages and a bilingual 404. Plain HTML, one CSS
file and two small JavaScript modules, published by GitHub Pages from `main` with the custom
domain in `CNAME`. Judgment calls are in `DECISIONS.md`; things only Gabe or Laurel can do are in
`NEEDS-GABE.md`.

Privacy-first like the app: no cookies, no browser storage, no analytics, no fonts or scripts
from other sites. Every file the pages load is in this repo, and the tests fail if a page load
makes a single request outside the site. Light and dark mode follow the device.

> The Privacy Policy and Terms of Use are drafts written to match the app. Have them reviewed
> (ideally by a lawyer, and the Spanish by a native speaker).

## Editing

The published pages are **generated**; edit the sources in `_src/`, then rebuild:

```
python3 _tools/build.py          # standard library only, no setup needed
python3 _tools/check_site.py     # must print OK
```

| What | Where |
| --- | --- |
| Home page layout | `_src/home.html` (`{{key}}` placeholders) |
| Home page wording | `_src/strings/en.json`, `_src/strings/es.json` |
| Support / Privacy / Terms | `_src/pages/en/*.html`, `_src/pages/es/*.html` (page content only) |
| 404 | `_src/pages/404.html` |
| Header, footer, `<head>` tags | `_tools/build.py` |
| App Store link, "Made by" name/photo/quote | `_src/config.json` |
| Styles | `assets/site.css` |
| Demo, calculator, scroll story, video | `assets/js/site.js`; scoring and summary text in `assets/js/demo-core.js` |

## App Store link (one place)

`appStoreURL` in `_src/config.json`. Empty = "Coming soon to the App Store" (not a link). When the
app is live:

```
python3 _tools/set_app_store_url.py https://apps.apple.com/app/id6824064215
python3 _tools/check_site.py && git commit -am "App Store link" && git push
```

That swaps both calls to action (hero and bottom of the page, English and Spanish) for Apple's
official badge linking to the app. `--coming-soon` switches back.

## Preview locally

```
cd /Users/laurelhamby/Developer/trialandtally-site
python3 _tools/devserver.py 8000
```

Then open http://localhost:8000/ (Ctrl+C to stop). `python3 -m http.server 8000` works too; the
dev server just also shows the custom 404 page like GitHub Pages does.

## Tests and review copies (dev tools, never published)

One-time setup (creates the git-ignored `.venv/` and downloads axe-core into `_tools/.cache/`):

```
bash _tools/setup_dev.sh
```

Then:

```
.venv/bin/python -m pytest _tools/tests          # everything (about 4 minutes)
.venv/bin/python _tools/make_review.py --screens # review screenshots into _review/
```

The browser tests use the Mac's Google Chrome, headless, one browser at a time:
- `test_demo_core.py`: the demo's scoring and summary text against cases from the app's own tests.
- `test_browser.py`: English and Spanish at 375x812, 1366x768 and 1440x900: no console errors, no
  requests outside the site, no horizontal scroll at 320 px, the demo by mouse and by keyboard,
  calculator, reduced motion, lazy video, language switch, axe-core (WCAG A/AA) with zero
  serious or critical problems, also in dark mode.
- `test_weight.py`: what the home page transfers before the video (budget 400 KB); numbers in
  `_review/weight.json`.
- `test_static.py`: `check_site.py`, pages in sync with `_src/`, the App Store switch, the
  "Made by" drop-in, Apple's badges unchanged, Support/Privacy/Terms content unchanged.

`python3 _tools/make_review.py` alone still writes the plain-text review copies of the English
Privacy, Terms and Support pages.

## Images and video

Made from the app repo's App Store assets (read only):

```
.venv/bin/python _tools/make_assets.py --video   # screenshots, icon layer, preview video, posters
.venv/bin/python _tools/make_share_images.py     # the 1200x630 link-preview images
```

Apple's badges in `assets/img/badges/` are unmodified downloads (see the README there).

## Pages (clean URLs: each is `folder/index.html`)
| English | Spanish |
| --- | --- |
| `/` | `/es/` |
| `/support/` | `/es/support/` |
| `/privacy/` (linked from the app's Settings and App Store Connect) | `/es/privacy/` |
| `/terms/` | `/es/terms/` |

Plus `404.html`, `CNAME`, `favicon-32.png`, `apple-touch-icon.png`, `app-icon.png` and `assets/`.
`_config.yml` keeps the notes, `_src/` and `_tools/` out of the published site.

## Publishing

`main` is live. Work happens on a branch (this redesign: `redesign`); merging into `main` and
pushing publishes it within a minute or two. GitHub Pages setup and DNS are in the app repo's
`NEEDS-GABE.md` (item 6).
