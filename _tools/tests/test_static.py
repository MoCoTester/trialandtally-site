"""Static checks that don't need a browser: the site checker, generated pages in sync, the
App Store switch, the "Made by a school SLP" drop-in, Apple's badges unchanged, and Support /
Privacy / Terms content unchanged from the pre-redesign site."""
import copy
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(TOOLS, f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("build")
check_site = load("check_site")


def test_check_site_passes(capsys):
    assert check_site.main() == 0, capsys.readouterr().out


def test_pages_up_to_date():
    assert subprocess.run([sys.executable, os.path.join(TOOLS, "build.py"), "--check"]).returncode == 0


def test_cname():
    assert open(os.path.join(ROOT, "CNAME")).read() == "trialandtally.com\n"


def test_badges_are_apples_unmodified_files():
    expected = {
        "app-store-badge-en.svg": "a26fc5b38380272c92e9019a2eb8b45542a66814b3e2b203772db8904b9fb99f",
        "app-store-badge-es.svg": "f5c911a6fb1861e0ba1007be5aa84162e8bc13ab6eebf953723ea3b282817be9",
    }
    for name, sha in expected.items():
        with open(os.path.join(ROOT, "assets", "img", "badges", name), "rb") as fh:
            assert hashlib.sha256(fh.read()).hexdigest() == sha, name


def config_with(**changes):
    config = copy.deepcopy(build.load_config())
    for key, value in changes.items():
        if isinstance(value, dict):
            config[key].update(value)
        else:
            config[key] = value
    return config


def test_coming_soon_until_url_is_set():
    assert build.load_config()["appStoreURL"] == "", "the app isn't released yet; keep 'Coming soon'"
    pages = build.build(config_with(appStoreURL=""))
    for rel, soon in (("index.html", "Coming soon to the App Store"), ("es/index.html", "Próximamente en el App Store")):
        assert pages[rel].count(soon) == 2  # hero and final call to action
        assert "apps.apple.com" not in pages[rel]
        assert "app-store-badge" not in pages[rel]


def test_app_store_url_lives_in_one_place():
    url = "https://apps.apple.com/app/id6824064215"
    pages = build.build(config_with(appStoreURL=url))
    for rel, lang, alt in (("index.html", "en", "Download on the App Store"), ("es/index.html", "es", "Descárgalo en el App Store")):
        html = pages[rel]
        assert html.count(f'href="{url}"') == 2
        assert html.count(f'src="/assets/img/badges/app-store-badge-{lang}.svg"') == 2
        assert f'alt="{alt}"' in html
        assert "Coming soon" not in html and "Próximamente" not in html
    # Nothing else in the sources or tools names the App Store link.
    for folder in ("_src", "assets", "_tools"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, folder)):
            dirnames[:] = [d for d in dirnames if d not in (".cache", "__pycache__", "tests")]
            for name in filenames:
                if name.endswith((".py", ".js", ".json", ".html", ".css")):
                    text = open(os.path.join(dirpath, name), encoding="utf-8").read()
                    assert "id6824064215" not in text or name == "set_app_store_url.py", name


def test_set_app_store_url_script(tmp_path):
    """The switch script edits only the value in config.json (run on a copy of the repo's config)."""
    script = load("set_app_store_url")
    original = open(script.CONFIG, encoding="utf-8").read()
    copy_path = tmp_path / "config.json"
    copy_path.write_text(original, encoding="utf-8")
    script.CONFIG = str(copy_path)
    script.subprocess.call = lambda *a, **k: 0  # don't rebuild the real pages
    sys.argv = ["set_app_store_url.py", "https://apps.apple.com/app/id6824064215"]
    assert script.main() == 0
    assert json.loads(copy_path.read_text())["appStoreURL"] == "https://apps.apple.com/app/id6824064215"
    assert copy_path.read_text().replace("https://apps.apple.com/app/id6824064215", "") == original
    sys.argv = ["set_app_store_url.py", "https://example.com/x"]
    with pytest.raises(SystemExit):
        script.main()


def test_maker_section_drop_in():
    plain = build.build()
    for rel in ("index.html", "es/index.html"):
        assert 'class="maker-photo"' not in plain[rel] and "<blockquote" not in plain[rel]
    pages = build.build(config_with(maker={
        "name": "Pat Example", "role_en": "School SLP", "role_es": "Terapeuta de lenguaje escolar",
        "photo": "/assets/img/icon-192.png", "photo_alt_en": "Pat smiling", "photo_alt_es": "Pat sonriendo",
        "quote_en": "I wanted my data sheet done before the next group walked in.",
        "quote_es": "Quería tener mi hoja de registro lista antes de que llegara el siguiente grupo."}))
    en, es = pages["index.html"], pages["es/index.html"]
    assert 'class="maker-photo" src="/assets/img/icon-192.png"' in en and 'alt="Pat smiling"' in en
    assert "<blockquote><p>I wanted my data sheet done" in en and "<figcaption>Pat Example, School SLP</figcaption>" in en
    assert 'alt="Pat sonriendo"' in es and "Terapeuta de lenguaje escolar</figcaption>" in es


def main_text(html):
    body = re.search(r"<main[^>]*>(.*?)</main>", html, re.S).group(1)
    return re.sub(r"\s+", " ", body).strip()


def strip_wrapper(text):
    return re.sub(r'^<div class="wrap prose"> | </div>$', "", text)


@pytest.mark.parametrize("rel", ["support/index.html", "privacy/index.html", "terms/index.html",
                                 "es/support/index.html", "es/privacy/index.html", "es/terms/index.html"])
def test_legal_and_support_content_unchanged(rel):
    """Support, Privacy and Terms keep the exact content they had before the redesign (commit
    71bd51f on main); only the page around it changed."""
    old = subprocess.run(["git", "-C", ROOT, "show", f"71bd51f:{rel}"], capture_output=True, text=True)
    if old.returncode != 0:
        pytest.skip("git history not available")
    new = open(os.path.join(ROOT, rel), encoding="utf-8").read()
    assert strip_wrapper(main_text(new)) == main_text(old.stdout)


def test_home_copy_has_no_unbacked_claims():
    """Honest copy: no testimonials, user counts, ratings or time-saved figures of our own."""
    for lang in ("en", "es"):
        text = json.dumps(json.load(open(os.path.join(ROOT, "_src", "strings", f"{lang}.json"), encoding="utf-8")),
                          ensure_ascii=False).lower()
        for banned in ("testimonial", "users love", "thousands", "5 stars", "5-star", "★", "saves you",
                       "save hours", "ahorra horas", "miles de", "#1", "best app", "la mejor app"):
            assert banned not in text, (lang, banned)


# ---------------------------------------------------------------- launch prep: sitemap, robots, social, Pinterest

SITE = "https://trialandtally.com"
INDEXED = {"index.html": "/", "support/index.html": "/support/", "privacy/index.html": "/privacy/",
           "terms/index.html": "/terms/", "es/index.html": "/es/", "es/support/index.html": "/es/support/",
           "es/privacy/index.html": "/es/privacy/", "es/terms/index.html": "/es/terms/"}
SOCIAL = {
    "Instagram": "https://www.instagram.com/trialandtally/",
    "Facebook": "https://www.facebook.com/trialandtally",
    "TikTok": "https://www.tiktok.com/@trialandtally",
    "YouTube": "https://www.youtube.com/@trialandtallyapp",
    "Pinterest": "https://www.pinterest.com/trialandtally/",
    "X": "https://x.com/trialandtally",
    "Threads": "https://www.threads.net/@trialandtally",
}
PINTEREST_TAG = '<meta name="p:domain_verify" content="36a3571c000689612ba0c30f00166bbd"/>'


def published(rel):
    return open(os.path.join(ROOT, rel), encoding="utf-8").read()


def test_sitemap_is_valid_xml_and_lists_every_page():
    import xml.etree.ElementTree as ET
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9", "x": "http://www.w3.org/1999/xhtml"}
    root = ET.fromstring(published("sitemap.xml").encode("utf-8"))  # raises if not well-formed
    assert root.tag == "{%s}urlset" % ns["s"]
    entries = {u.findtext("s:loc", namespaces=ns): {l.get("hreflang"): l.get("href") for l in u.findall("x:link", ns)}
               for u in root.findall("s:url", ns)}
    assert set(entries) == {SITE + path for path in INDEXED.values()}
    assert SITE + "/404.html" not in entries
    for rel, path in INDEXED.items():
        en_path = path[3:] if path.startswith("/es/") else path
        assert entries[SITE + path] == {"en": SITE + en_path, "es": SITE + "/es" + en_path, "x-default": SITE + en_path}
        # Every page in the sitemap exists and isn't noindex.
        assert "noindex" not in published(rel)
    # Every published HTML page except the 404 is in the sitemap.
    html_pages = set()
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith(("_", "."))]  # unpublished: _src, _tools, .venv...
        html_pages |= {os.path.relpath(os.path.join(d, f), ROOT) for f in files if f.endswith(".html")}
    assert html_pages - {"404.html"} == set(INDEXED)


def test_robots_txt_points_to_sitemap():
    lines = published("robots.txt").splitlines()
    assert "Sitemap: https://trialandtally.com/sitemap.xml" in lines
    assert "User-agent: *" in lines and "Disallow: /" not in lines


def test_sitemap_and_robots_rebuild_with_the_pages():
    pages = build.build()
    assert pages["sitemap.xml"] == published("sitemap.xml")
    assert pages["robots.txt"] == published("robots.txt")


@pytest.mark.parametrize("rel,label,on", [
    (rel, *(("Trial&amp;Tally en redes sociales", "Trial&amp;Tally en") if rel.startswith("es/")
            else ("Trial&amp;Tally on social media", "Trial&amp;Tally on")))
    for rel in list(INDEXED) + ["404.html"]])
def test_footer_social_links(rel, label, on):
    footer = re.search(r'<footer class="site-footer">.*?</footer>', published(rel), re.S).group(0)
    social = re.search(r'<ul class="footer-social" aria-label="([^"]+)">(.*?)</ul>', footer, re.S)
    assert social and social.group(1) == label
    links = re.findall(r'<li><a href="([^"]+)" rel="me"><svg ([^>]+)><path d="[^"]+"/></svg>'
                       r'<span class="sr-only">([^<]+)</span></a></li>', social.group(2))
    assert [(href, name) for href, _, name in links] == [(url, f"{on} {n}") for n, url in SOCIAL.items()]
    for _, svg_attrs, _ in links:
        assert 'aria-hidden="true"' in svg_attrs and 'focusable="false"' in svg_attrs
    assert "target=" not in social.group(2)


def test_pinterest_tag_on_home_pages_only():
    assert build.load_config()["pinterest_verify"] == "36a3571c000689612ba0c30f00166bbd"
    for rel in INDEXED:
        html = published(rel)
        head = html[:html.index("</head>")]
        if rel in ("index.html", "es/index.html"):
            assert head.count(PINTEREST_TAG) == 1, rel
        else:
            assert "p:domain_verify" not in html, rel


def test_smart_app_banner_switches_with_the_app_store_url():
    """Safari's Smart App Banner (Apple's own, no request to another site) appears on every indexed
    page once appStoreURL is set, with the ID taken from the URL; never before launch."""
    for rel, html in build.build(config_with(appStoreURL="")).items():
        assert "apple-itunes-app" not in html, rel
    pages = build.build(config_with(appStoreURL="https://apps.apple.com/app/id6824064215"))
    for rel in INDEXED:
        assert pages[rel].count('<meta name="apple-itunes-app" content="app-id=6824064215">') == 1, rel
    assert "apple-itunes-app" not in pages["404.html"]
