#!/usr/bin/env python3
"""
Pinterest Bulk Downloader
=========================
Download images from Pinterest searches or boards by topic, filter out the bad
ones, and top up automatically. No API key needed: it drives a real Chromium
browser that you log in to yourself.

Commands
  python pinterest_downloader.py download   download up to --target images per topic
  python pinterest_downloader.py filter     remove corrupt / tiny / near-duplicate images
  python pinterest_downloader.py status     show kept / rejected counts per topic

Typical loop
  download -> filter -> (delete images you dislike by hand) -> download
  The second download tops each topic back up and never re-downloads rejected images.

Options
  --target N          images to keep per topic         (default 500)
  --topics FILE       topics file, one per line        (default topics.txt)
  --min-size PIXELS   minimum width and height         (default 500)

For personal, educational use only. Pinterest's terms restrict automated access
and the images belong to their creators. See README.md.
"""
import argparse
import json
import random
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote_plus

import requests
from PIL import Image

__version__ = "1.0.0"

# ----------------------------- CONFIG ---------------------------------
TARGET = 500                          # images to keep per topic
TOPICS_FILE = "topics.txt"            # one topic (search phrase or board URL) per line
OUT_DIR = Path("downloads")
MIN_W, MIN_H = 500, 500               # filter: minimum image size
THREADS = 4                           # parallel downloads (keep it gentle)
PROFILE_DIR = str(Path("pinterest_profile").resolve())   # saved login session
MAX_IDLE_SCROLLS = 8                  # stop scrolling after this many empty scrolls
# -----------------------------------------------------------------------

PIN_RE = re.compile(r"https://i\.pinimg\.com/(\d+x|originals)/(.+?)/([0-9a-f]{20,})\.(jpg|png|webp)")


# ---------------------------- helpers ---------------------------------
def slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:80] or "topic"


def load_topics():
    f = Path(TOPICS_FILE)
    if not f.exists():
        sys.exit(f"Topics file '{TOPICS_FILE}' not found. Create it with one topic per line.")
    topics = []
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            topics.append(line)
    if not topics:
        sys.exit(f"'{TOPICS_FILE}' is empty. Add one topic per line.")
    return topics


# --------------------------- manifest ---------------------------------
# Remembers every image ever downloaded ("kept" or "rejected") so that images
# you delete or filter out are never downloaded again.
def manifest_path(topic_dir):
    return topic_dir / "manifest.json"


def load_manifest(topic_dir):
    p = manifest_path(topic_dir)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save_manifest(topic_dir, m):
    manifest_path(topic_dir).write_text(json.dumps(m, indent=1), encoding="utf-8")


def sync_with_disk(topic_dir, m):
    """Files you deleted by hand are marked rejected."""
    changed = 0
    for info in m.values():
        if info["status"] == "kept" and not (topic_dir / info["file"]).exists():
            info["status"] = "rejected"
            changed += 1
    return changed


def kept_count(m):
    return sum(1 for i in m.values() if i["status"] == "kept")


# ---------------------------- browser ---------------------------------
_state = {"pw": None, "ctx": None, "page": None}


def _launch(pw):
    return pw.chromium.launch_persistent_context(
        PROFILE_DIR, headless=False, viewport={"width": 1280, "height": 900}
    )


def get_page():
    """Open Chromium once (installing it on first run) and let the user log in."""
    if _state["page"]:
        return _state["page"]
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Playwright is not installed. Run: pip install -r requirements.txt")

    pw = sync_playwright().start()
    try:
        ctx = _launch(pw)
    except Exception as e:
        if "playwright install" in str(e) or "Executable doesn't exist" in str(e):
            print("First run: downloading Chromium (one time, ~150 MB)...")
            subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
            ctx = _launch(pw)
        else:
            pw.stop()
            raise

    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto("https://www.pinterest.com/")
    input("\nLog in to Pinterest in the browser window (skip if already logged in),\n"
          "then press Enter here to continue... ")
    _state.update(pw=pw, ctx=ctx, page=page)
    return page


def close_browser():
    if _state["ctx"]:
        try:
            _state["ctx"].close()
            _state["pw"].stop()
        except Exception:
            pass
        _state.update(pw=None, ctx=None, page=None)


def search_pinterest(topic):
    """Yield (pin_id, image_url) while scrolling a Pinterest search or board."""
    page = get_page()
    url = topic if topic.startswith("http") else \
        f"https://www.pinterest.com/search/pins/?q={quote_plus(topic)}"
    page.goto(url)
    time.sleep(4)

    seen, idle = set(), 0
    while idle < MAX_IDLE_SCROLLS:
        srcs = page.eval_on_selector_all("img", "els => els.map(e => e.src)")
        new = 0
        for s in srcs:
            m = PIN_RE.match(s or "")
            if not m:
                continue
            pid = m.group(3)
            if pid in seen:
                continue
            seen.add(pid)
            new += 1
            # reliable mid-size URL; download_one tries the original first
            yield pid, f"https://i.pinimg.com/736x/{m.group(2)}/{pid}.{m.group(4)}"
        idle = 0 if new else idle + 1
        page.mouse.wheel(0, 2500)
        time.sleep(random.uniform(1.5, 3.0))


def download_one(args):
    """Download one image: original resolution first, then the 736px fallback."""
    pid, url, dest = args
    original = url.replace("/736x/", "/originals/")
    for u in (original, url):
        try:
            with requests.get(u, stream=True, timeout=60) as r:
                if r.status_code != 200:
                    continue
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(65536):
                        f.write(chunk)
            return pid, True
        except Exception:
            Path(dest).unlink(missing_ok=True)
    print(f"  failed {pid}")
    return pid, False


# ---------------------------- commands --------------------------------
def cmd_download(_):
    for topic in load_topics():
        topic_dir = OUT_DIR / slug(topic)
        topic_dir.mkdir(parents=True, exist_ok=True)
        m = load_manifest(topic_dir)

        gone = sync_with_disk(topic_dir, m)
        if gone:
            print(f"[{topic}] {gone} files missing from disk -> marked rejected")

        need = TARGET - kept_count(m)
        print(f"[{topic}] kept={kept_count(m)} need={max(need, 0)}")
        if need <= 0:
            save_manifest(topic_dir, m)
            continue

        batch = []
        for pid, url in search_pinterest(topic):
            if pid in m:
                continue          # already have it, or rejected before
            batch.append((pid, url, topic_dir / f"{pid}{Path(url).suffix}"))
            if len(batch) >= need:
                break

        dests = {pid: dest for pid, _url, dest in batch}
        with ThreadPoolExecutor(THREADS) as ex:
            for i, (pid, ok) in enumerate(ex.map(download_one, batch), 1):
                if ok:
                    m[pid] = {"file": dests[pid].name, "status": "kept"}
                if i % 50 == 0:
                    print(f"  {i}/{len(batch)}")
                    save_manifest(topic_dir, m)

        save_manifest(topic_dir, m)
        print(f"[{topic}] done, kept={kept_count(m)}")
        if kept_count(m) < TARGET:
            print(f"  Pinterest ran out of results for '{topic}'. "
                  f"Try related topics or a board URL.")


def average_hash(img, size=8):
    g = img.convert("L").resize((size, size))
    px = list(g.getdata())
    avg = sum(px) / len(px)
    return sum(1 << i for i, v in enumerate(px) if v > avg)


def cmd_filter(_):
    for topic in load_topics():
        topic_dir = OUT_DIR / slug(topic)
        if not topic_dir.exists():
            continue
        m = load_manifest(topic_dir)
        sync_with_disk(topic_dir, m)
        hashes, removed = [], 0

        for info in m.values():
            if info["status"] != "kept":
                continue
            path = topic_dir / info["file"]
            reason = None
            try:
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    w, h = img.size
                    if w < MIN_W or h < MIN_H:
                        reason = f"too small {w}x{h}"
                    else:
                        hsh = average_hash(img)
                        if any(bin(hsh ^ o).count("1") <= 4 for o in hashes):
                            reason = "near-duplicate"
                        else:
                            hashes.append(hsh)
            except Exception:
                reason = "corrupt"

            if reason:
                path.unlink(missing_ok=True)
                info["status"] = "rejected"
                removed += 1
                print(f"  removed {info['file']}: {reason}")

        save_manifest(topic_dir, m)
        print(f"[{topic}] removed {removed}, kept {kept_count(m)}")
    print("\nRun `python pinterest_downloader.py download` to top back up to the target.")


def cmd_status(_):
    for topic in load_topics():
        topic_dir = OUT_DIR / slug(topic)
        m = load_manifest(topic_dir) if topic_dir.exists() else {}
        if m:
            sync_with_disk(topic_dir, m)
        rejected = sum(1 for i in m.values() if i["status"] == "rejected")
        print(f"{topic[:40]:40} kept={kept_count(m):5} rejected={rejected:5} target={TARGET}")


def main(argv=None):
    global TARGET, TOPICS_FILE, MIN_W, MIN_H
    ap = argparse.ArgumentParser(
        prog="pinterest_downloader.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--version", action="version", version=__version__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", type=int, help=f"images to keep per topic (default {TARGET})")
    common.add_argument("--topics", help="topics file, one per line (default topics.txt)")
    common.add_argument("--min-size", type=int, help=f"minimum width/height in pixels (default {MIN_W})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("download", parents=[common], help="download images").set_defaults(fn=cmd_download)
    sub.add_parser("filter", parents=[common], help="remove bad images").set_defaults(fn=cmd_filter)
    sub.add_parser("status", parents=[common], help="show counts").set_defaults(fn=cmd_status)
    args = ap.parse_args(argv)

    if args.target:
        TARGET = args.target
    if args.topics:
        TOPICS_FILE = args.topics
    if args.min_size:
        MIN_W = MIN_H = args.min_size

    try:
        args.fn(args)
    except KeyboardInterrupt:
        print("\nStopped. Progress so far is saved; run download again to continue.")
    finally:
        close_browser()


if __name__ == "__main__":
    main()
