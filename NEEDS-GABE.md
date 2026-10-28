# Needs Gabe (or Laurel)

Things Claude can't or shouldn't decide for the website. Paths are in this repo,
`/Users/laurelhamby/Developer/trialandtally-site`.

## 1. Review and approve the redesign (branch `redesign`)
The live site (`main`) is unchanged. Preview the branch on your Mac:

```
cd /Users/laurelhamby/Developer/trialandtally-site
git checkout redesign
python3 _tools/devserver.py 8000
```

Open http://localhost:8000/ (and http://localhost:8000/es/). Review screenshots are in `_review/`
after `.venv/bin/python _tools/make_review.py --screens`. Items marked (review) in `DECISIONS.md`
are the judgment calls worth a look.

To publish once approved:

```
git checkout main
git merge --ff-only redesign
git push
```

(or open a pull request from `redesign` on GitHub and merge it there). After it's live, paste
https://trialandtally.com into a Facebook post draft or an iMessage to see the new link preview.
Facebook caches previews; its Sharing Debugger can refresh it.

## 2. When the app is on the App Store
One line switches both "Coming soon to the App Store" spots (English and Spanish) to Apple's
official badge linking to the app:

```
python3 _tools/set_app_store_url.py https://apps.apple.com/app/id6824064215
python3 _tools/check_site.py && git commit -am "App Store link" && git push
```

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
