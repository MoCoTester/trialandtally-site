#!/usr/bin/env python3
"""Makes the home page's images and videos from the app repo's App Store assets.

Run with the dev venv (see README): .venv/bin/python _tools/make_assets.py [--video]

Reads (never writes) /Users/laurelhamby/Developer/TrialAndTally:
  AppStoreScreenshots/iPhone-6.9/*.png (English), AppStoreScreenshots/es/iPhone-6.9/*.png (Spanish)
  AppStorePreviews/{en,es}/iPhone-6.9/01-preview.mov (+ 01-preview.poster.txt)
  AppIconConcepts/final-icon-1024.png
Writes assets/img/... and (with --video) assets/video/... in this repo (H.264 MP4 only: a VP9
WebM came out larger than the MP4 for this mostly-still footage). The outputs are committed,
so GitHub Pages never needs this script.
"""
import argparse
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.environ.get("TT_APP_REPO", "/Users/laurelhamby/Developer/TrialAndTally")
IMG = os.path.join(ROOT, "assets", "img")
VIDEO = os.path.join(ROOT, "assets", "video")

# Screens used on the home page: the hero phone (01) and the five "How it works" steps.
SHOTS = ["01-session", "02-prompt", "03-summary", "04-add-student", "05-clear"]
SHOT_WIDTHS = [300, 600, 900]
SHOT_DIRS = {"en": "AppStoreScreenshots/iPhone-6.9", "es": "AppStoreScreenshots/es/iPhone-6.9"}

# Where the bars and check sit in the 1024 px icon (measured from final-icon-1024.png). The hero
# draws them in SVG on top of icon-base (the icon with that area painted over with the background).
BARS_BOX = (280, 500, 760, 905)


def save_set(im, base, widths, jpg_width=None):
    """Writes base-<w>.avif and base-<w>.webp for each width (+ base-<jpg_width>.jpg)."""
    os.makedirs(os.path.dirname(base), exist_ok=True)
    for w in widths:
        h = round(im.height * w / im.width)
        small = im.resize((w, h), Image.LANCZOS)
        small.save(f"{base}-{w}.avif", quality=58, speed=4)
        small.save(f"{base}-{w}.webp", quality=80, method=6)
    if jpg_width:
        h = round(im.height * jpg_width / im.width)
        im.resize((jpg_width, h), Image.LANCZOS).save(f"{base}-{jpg_width}.jpg", quality=80,
                                                      optimize=True, progressive=True)


def screenshots():
    for lang, rel in SHOT_DIRS.items():
        for name in SHOTS:
            src = os.path.join(APP, rel, name + ".png")
            im = Image.open(src).convert("RGB")
            save_set(im, os.path.join(IMG, "shots", lang, name), SHOT_WIDTHS, jpg_width=600)
            print("shot", lang, name)


def icon():
    im = Image.open(os.path.join(APP, "AppIconConcepts", "final-icon-1024.png")).convert("RGB")
    px = im.load()
    x0, y0, x1, y1 = BARS_BOX
    for y in range(y0, y1):
        bg = px[60, y]  # the background is a vertical gradient: copy the row's edge color
        for x in range(x0, x1):
            px[x, y] = bg
    base = os.path.join(IMG, "icon-base")
    for w in (192, 384):
        small = im.resize((w, w), Image.LANCZOS)
        small.save(f"{base}-{w}.webp", quality=88, method=6)
        small.save(f"{base}-{w}.png", optimize=True)
    # The full icon (for the final call to action and the share image).
    full = Image.open(os.path.join(APP, "AppIconConcepts", "final-icon-1024.png")).convert("RGB")
    for w in (192, 384):
        full.resize((w, w), Image.LANCZOS).save(os.path.join(IMG, f"icon-{w}.png"), optimize=True)
        full.resize((w, w), Image.LANCZOS).save(os.path.join(IMG, f"icon-{w}.webp"), quality=88, method=6)
    print("icon")


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def videos():
    os.makedirs(VIDEO, exist_ok=True)
    exe = ffmpeg()
    for lang in ("en", "es"):
        src = os.path.join(APP, "AppStorePreviews", lang, "iPhone-6.9", "01-preview.mov")
        poster_time = open(src.replace(".mov", ".poster.txt")).read().strip()
        out = os.path.join(VIDEO, f"preview-{lang}")
        # 886x1920 -> 590x1280: still sharper than the ~300 CSS px it shows at on a 2x screen.
        # The App Store previews are BT.709 but untagged: convert and tag as BT.709 so browsers
        # show the app's exact green (#1B7A34) instead of a brighter BT.601 reading.
        scale = "scale=590:1280:flags=lanczos:in_color_matrix=bt709:out_color_matrix=bt709"
        tags = ["-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
        run([exe, "-y", "-v", "error", "-i", src, "-an", "-vf", scale, "-c:v", "libx264",
             "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "veryslow", "-crf", "20",
             "-tune", "animation", *tags, "-movflags", "+faststart", out + ".mp4"])
        # Poster: the "One tap per trial" moment (same time as the App Store poster frame).
        png = os.path.join(VIDEO, f"poster-{lang}.png")
        run([exe, "-y", "-v", "error", "-ss", poster_time, "-i", src, "-vf",
             "scale=in_color_matrix=bt709:out_color_matrix=bt709", "-frames:v", "1", png])
        poster = Image.open(png).convert("RGB")
        os.remove(png)
        # WebP only: <video poster> takes one URL, and every browser that plays this MP4 shows WebP.
        poster.resize((600, round(poster.height * 600 / poster.width)), Image.LANCZOS).save(
            os.path.join(IMG, f"poster-{lang}-600.webp"), quality=80, method=6)
        print(f"video {lang}: {os.path.getsize(out + '.mp4') / 1e6:.2f} MB")


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", action="store_true", help="also re-encode the preview videos (slow)")
    args = ap.parse_args()
    if not os.path.isdir(APP):
        sys.exit(f"App repo not found at {APP} (set TT_APP_REPO)")
    screenshots()
    icon()
    if args.video:
        videos()


if __name__ == "__main__":
    main()
