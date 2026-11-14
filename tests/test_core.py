"""Offline tests: run with  python -m unittest discover -s tests
They replace the Pinterest browser/network parts with fakes, so they need
no internet and no login."""
import os
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image  # noqa: E402

import pinterest_downloader as pd  # noqa: E402


def make_image(path, size=(800, 800), seed=0):
    rnd = random.Random(seed)
    img = Image.new("RGB", (8, 8))
    img.putdata([(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)) for _ in range(64)])
    img.resize(size, Image.NEAREST).save(path, "JPEG")


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmp.name)
        Path("topics.txt").write_text("# comment\nsunset sky\n\n", encoding="utf-8")
        pd.OUT_DIR = Path("downloads")
        pd.TARGET = 10
        pd.TOPICS_FILE = "topics.txt"
        pd.MIN_W = pd.MIN_H = 500
        self.fake_pool = [(f"{i:020x}", f"https://i.pinimg.com/736x/aa/bb/{i:020x}.jpg") for i in range(1, 200)]
        self.downloaded = []

        def fake_search(topic):
            yield from self.fake_pool

        def fake_download(args):
            pid, url, dest = args
            self.downloaded.append(pid)
            n = int(pid, 16)
            if n == 3:
                Path(dest).write_bytes(b"not an image")          # corrupt
            elif n == 4:
                make_image(dest, (200, 200), seed=n)              # too small
            elif n == 6:
                make_image(dest, (800, 800), seed=5)              # duplicate of #5
            else:
                make_image(dest, (800, 800), seed=n)
            return pid, True

        pd.search_pinterest = fake_search
        pd.download_one = fake_download

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.tmp.cleanup()

    def topic_dir(self):
        return pd.OUT_DIR / pd.slug("sunset sky")

    def test_topics_ignore_comments_and_blanks(self):
        self.assertEqual(pd.load_topics(), ["sunset sky"])

    def test_download_reaches_target(self):
        pd.main(["download"])
        m = pd.load_manifest(self.topic_dir())
        self.assertEqual(pd.kept_count(m), 10)
        self.assertEqual(len(list(self.topic_dir().glob("*.jpg"))), 10)

    def test_filter_then_topup_never_redownloads(self):
        pd.main(["download"])
        first = set(self.downloaded)
        pd.main(["filter"])
        m = pd.load_manifest(self.topic_dir())
        rejected = {k for k, v in m.items() if v["status"] == "rejected"}
        self.assertEqual(len(rejected), 3)   # corrupt + small + duplicate
        self.downloaded.clear()
        pd.main(["download"])
        m = pd.load_manifest(self.topic_dir())
        self.assertEqual(pd.kept_count(m), 10)
        self.assertFalse(first & set(self.downloaded), "previously downloaded images were fetched again")

    def test_manual_delete_is_rejected_and_replaced(self):
        pd.main(["download"])
        victims = sorted(self.topic_dir().glob("*.jpg"))[:4]
        names = {v.name for v in victims}
        for v in victims:
            v.unlink()
        self.downloaded.clear()
        pd.main(["download"])
        m = pd.load_manifest(self.topic_dir())
        self.assertEqual(pd.kept_count(m), 10)
        self.assertEqual(len(list(self.topic_dir().glob("*.jpg"))), 10)
        self.assertFalse(names & {f"{p}.jpg" for p in self.downloaded})

    def test_target_and_min_size_flags(self):
        pd.main(["download", "--target", "5"])
        self.assertEqual(pd.kept_count(pd.load_manifest(self.topic_dir())), 5)
        pd.main(["filter", "--min-size", "900"])   # everything is 800px -> all removed
        self.assertEqual(pd.kept_count(pd.load_manifest(self.topic_dir())), 0)


if __name__ == "__main__":
    unittest.main()
