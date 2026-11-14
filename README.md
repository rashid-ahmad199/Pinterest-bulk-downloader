# Pinterest Bulk Downloader

[![tests](https://github.com/rashid-ahmad199/Pinterest-bulk-downloader/actions/workflows/tests.yml/badge.svg)](https://github.com/rashid-ahmad199/Pinterest-bulk-downloader/actions/workflows/tests.yml)
![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.10%2B-blue)

Download **500 images per topic** (or any number you choose) from Pinterest searches
or boards, filter out the bad ones, and top up automatically. Great for collecting
design inspiration: website UI, t-shirt designs, logos, moodboards.

- **No API key, no third-party service.** It opens a real Chromium browser and you log in yourself.
- Chromium is installed for you by the setup script.
- Several topics in one run, each saved in its own folder.
- `filter` removes corrupt, tiny and near-duplicate images.
- Delete images you don't like, run `download` again, and it tops back up to the target
  **without re-downloading the ones you rejected**.

---

## Quick start (Windows PowerShell)

Requires [Python 3.10+](https://www.python.org/downloads/) (tick **Add python.exe to PATH** when installing)
and [Git](https://git-scm.com/downloads).

```powershell
# 1. get the project
git clone https://github.com/rashid-ahmad199/Pinterest-bulk-downloader.git
cd Pinterest-bulk-downloader

# 2. one-time setup (creates .venv, installs requirements, downloads Chromium)
powershell -ExecutionPolicy Bypass -File .\setup.ps1

# 3. put your topics in topics.txt (one per line), then download
notepad topics.txt
powershell -ExecutionPolicy Bypass -File .\run.ps1 download
```

A Chromium window opens. **Log in to Pinterest**, go back to PowerShell and press **Enter**.
Your login is saved in `pinterest_profile/`, so you only do this once.

Images are saved in `downloads\<topic>\`. Open the folder with:

```powershell
explorer downloads
```

> Tip: to type `.\run.ps1 download` without the long prefix, allow local scripts once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### The everyday loop

```powershell
.\run.ps1 download      # download up to 500 per topic
.\run.ps1 filter        # remove corrupt / tiny / near-duplicate images
# (optional) delete images you dislike by hand from downloads\<topic>\
.\run.ps1 download      # tops each topic back up to 500, never re-downloads rejected ones
.\run.ps1 status        # kept / rejected counts per topic
```

### Options

```powershell
.\run.ps1 download -Target 1000                          # 1000 per topic
.\run.ps1 download -Topics topics\tshirt_design.txt      # use another topics file
.\run.ps1 download -Topics topics\website_ui.txt -Target 300
.\run.ps1 filter -MinSize 800                            # stricter size filter
```

---

## Quick start (macOS / Linux, or without the scripts)

```bash
git clone https://github.com/rashid-ahmad199/Pinterest-bulk-downloader.git
cd Pinterest-bulk-downloader
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium

python pinterest_downloader.py download
python pinterest_downloader.py filter
python pinterest_downloader.py status
python pinterest_downloader.py download --target 1000 --topics topics/tshirt_design.txt
```

| Option | Meaning | Default |
|--------|---------|---------|
| `--target N` | images to keep per topic | 500 |
| `--topics FILE` | topics file, one per line | `topics.txt` |
| `--min-size PX` | minimum width and height used by `filter` | 500 |

---

## Topics

`topics.txt` has one topic per line. A line can be a search phrase or a board URL, and
lines starting with `#` are ignored:

```
website hero section design
https://www.pinterest.com/yourname/your-board/
```

Ready-made lists:

| File | Topics |
|------|--------|
| `topics/website_ui.txt` | hero, footer, login, sign up, navbar, pricing, testimonials, contact, dashboard, features |
| `topics/tshirt_design.txt` | creative, typography, streetwear, minimalist, vintage, anime, funny quotes, aesthetic, logo, mockups |

## Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests run offline with a fake Pinterest source and also run automatically on GitHub.

## Troubleshooting

- **"running scripts is disabled on this system":** use the full form
  `powershell -ExecutionPolicy Bypass -File .\run.ps1 download`.
- **`python` not found:** install Python from python.org and tick "Add python.exe to PATH", then reopen PowerShell.
- **Stops below the target:** Pinterest stops loading new pins after a while.
  Use several related topics or a board URL.
- **Nothing is found:** make sure you are logged in and the Chromium window shows pins before you press Enter.
- **Start a topic over:** delete its folder in `downloads\`.
- **Log in as someone else:** delete the `pinterest_profile\` folder.

## Notes

- The script scrolls at a human pace on purpose. Don't run it for hours;
  Pinterest can limit accounts that use heavy automation.
- Never commit `pinterest_profile/`. It holds your login session (already in `.gitignore`).

## Disclaimer

For **personal, educational use only**. Pinterest's terms restrict automated access,
and the images belong to their creators. Use downloaded images as inspiration only:
don't redistribute them and don't copy designs to sell. You are responsible for how
you use this tool. This project is not affiliated with Pinterest.

## License

MIT, see [LICENSE](LICENSE).
