#!/usr/bin/env python3
"""Switches the site's App Store call to action (standard library only).

  python3 _tools/set_app_store_url.py https://apps.apple.com/app/id6824064215   # app is live
  python3 _tools/set_app_store_url.py --coming-soon                             # back to "Coming soon"

Sets "appStoreURL" in _src/config.json (the one place the link lives), then rebuilds the pages.
Then check, commit and push: python3 _tools/check_site.py && git commit -am "App Store link" && git push
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "_src", "config.json")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    url = "" if sys.argv[1] == "--coming-soon" else sys.argv[1].strip()
    if url and not re.fullmatch(r"https://apps\.apple\.com/[\w/.\-?=&]+", url):
        sys.exit(f"Not an App Store link: {url}")
    with open(CONFIG, encoding="utf-8") as fh:
        text = fh.read()
    json.loads(text)  # must be valid before we touch it
    # Replace just the value so the file's comments and layout stay as they are.
    new = re.sub(r'("appStoreURL":\s*)"[^"]*"', lambda m: m.group(1) + json.dumps(url), text, count=1)
    with open(CONFIG, "w", encoding="utf-8") as fh:
        fh.write(new)
    print("appStoreURL =", url or "(empty: Coming soon to the App Store)")
    return subprocess.call([sys.executable, os.path.join(ROOT, "_tools", "build.py")])


if __name__ == "__main__":
    sys.exit(main())
