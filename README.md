> **DRAFT — review before publishing.** The Privacy Policy (`/privacy`, `/es/privacy`) and
> Terms of Use (`/terms`, `/es/terms`) are drafts written to match the app. Have them reviewed
> (ideally by a lawyer, and the Spanish by a native speaker) before the site goes live.

# trialandtally.com

Static site for the Trial&Tally iPhone/iPad app. Plain HTML + one CSS file, ready for
GitHub Pages with the custom domain `trialandtally.com` (see `CNAME`).

Privacy-first like the app: no JavaScript, no analytics, no cookies, no external fonts or CDNs,
no forms. Light and dark mode follow the device (`prefers-color-scheme`).

## Pages (clean URLs: each is `folder/index.html`)
| English | Spanish |
| --- | --- |
| `/` | `/es/` |
| `/support` | `/es/support` |
| `/privacy` (linked from the app's Settings) | `/es/privacy` |
| `/terms` | `/es/terms` |

Plus `404.html` (bilingual), `styles.css`, `favicon.svg`, `CNAME`.
`_config.yml` keeps this README and `_tools/` out of the published site.

## Before publishing
1. Review the Privacy Policy and Terms (see the note at the top).
2. After the app is live, replace the "Coming soon to the App Store" badge on `/` and `/es/`
   with the real App Store link (search for `App Store link placeholder`).
3. Optionally link Apple's Standard EULA from `/terms` (left as plain text so the site has no
   external links yet).
4. Run the checker: `python3 _tools/check_site.py` (must print `OK`).

## Publishing
Pushed to https://github.com/MoCoTester/trialandtally-site (branch `main`). GitHub Pages setup
(source: `main`, root; custom domain `trialandtally.com`; Enforce HTTPS) and the Squarespace DNS
records are listed step by step in the app repo's `NEEDS-GABE.md` (item 6).

`_review/` (git-ignored) holds plain-text copies of the English Privacy Policy, Terms, and Support
pages for review. Regenerate them after editing a page: `python3 _tools/make_review.py`.

## Preview locally
`python3 -m http.server 8000` in this folder, then open http://localhost:8000.
