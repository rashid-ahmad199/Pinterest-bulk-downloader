# Changelog

## v1.0.0 - First release
- Bulk download Pinterest images by search topic or board URL (500 per topic by default)
- No API key and no third-party service: drives a real Chromium browser that you log in to yourself
- PowerShell `setup.ps1` (venv + requirements + Chromium) and `run.ps1` (download / filter / status)
- `filter` command removes corrupt, tiny and near-duplicate images
- Auto top-up: `download` only fetches what is missing, rejected images are never downloaded again
- Images you delete by hand are detected and replaced on the next `download`
- Options: `--target`, `--topics`, `--min-size`
- Ready-made topic lists for website UI and t-shirt design inspiration
- Offline unit tests and GitHub Actions CI
