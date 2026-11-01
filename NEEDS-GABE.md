# Needs Gabe (or Laurel)

Things Claude can't or shouldn't decide for the website. Paths are in this repo,
`/Users/laurelhamby/Developer/trialandtally-site`.

## 1. Pinterest: verify the website claim (now)
Pinterest: click Verify on the website claim (Settings → Claimed accounts) now that the tag is live.
The tag (`<meta name="p:domain_verify" content="36a3571c000689612ba0c30f00166bbd"/>`) has been on
https://trialandtally.com/ and /es/ since 2026-11-01; the value lives in `_src/config.json` →
`pinterest_verify`. Don't remove it after verifying (Pinterest re-checks it).

## 2. When the app is on the App Store
Follow `/Users/laurelhamby/Developer/TrialAndTally/Marketing/LAUNCH-DAY.md` (steps 3 and 4 are the
website). The one command:

```
cd /Users/laurelhamby/Developer/trialandtally-site && python3 _tools/set_app_store_url.py https://apps.apple.com/app/id6824064215 && python3 _tools/check_site.py && git commit -am "App Store link" && git push
```

It switches both "Coming soon to the App Store" spots (English and Spanish) to Apple's official
badge linking to the app, and adds Safari's Smart App Banner to every page.

## 2b. Google Search Console: submit the sitemap (any time)
https://search.google.com/search-console → trialandtally.com → Sitemaps → type `sitemap.xml` →
Submit. It's live at https://trialandtally.com/sitemap.xml (8 pages, English and Spanish).

## 3. "Made by a school SLP": name, photo and quote (optional, Laurel's call)
The section shows a short paragraph without a name today. If Laurel wants to be named, fill in
`_src/config.json` → `maker`, then run `python3 _tools/build.py`:

| Field | Example |
| --- | --- |
| `name` | `Laurel Hamby` (or how she'd like to be credited) |
| `role_en` / `role_es` | `School speech-language pathologist` / `Terapeuta de lenguaje escolar` |
| `photo` | `/assets/img/maker.jpg` (square, at least 320x320, put the file in `assets/img/`) |
| `photo_alt_en` / `photo_alt_es` | a short description of the photo |
| `quote_en` / `quote_es` | one or two sentences in her words, both languages |

Any field can stay empty: name only, quote only, or photo only all work. `test_static.py` checks
the drop-in. Run the tests after adding a photo (the page weight budget includes it; keep the JPG
under ~40 KB).

## 4. Spanish review
The new home page wording is in `_src/strings/es.json` (Mexican / Latin American Spanish, matching
the app). A native speaker, ideally an SLP, should read it. Edit the file, then
`python3 _tools/build.py`.

## 5. Later
- Tester or customer quotes: only real ones, with permission. There is no testimonials section
  yet; ask Claude to add one when you have quotes.
- The Privacy Policy and Terms are still drafts (see README).
