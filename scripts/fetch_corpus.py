"""Fetch or list candidate insurer PDFs for manual review."""

from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


CORPUS_URLS = {
    "aami_home_contents": "https://www.aami.com.au/aami/documents/pds/home-contents-insurance-pds.pdf",
    "allianz_home_contents": "https://www.allianz.com.au/content/dam/onemarketing/azau/allianz-com-au/documents/personal/home-insurance/home-and-contents-key-facts-sheet.pdf",
    "budget_direct_home_contents": "https://www.budgetdirect.com.au/content/dam/budgetdirect/website-assets/documents/home-insurance/home-and-contents-pds.pdf",
}


def fetch_corpus(output_dir: Path, *, download: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, url in CORPUS_URLS.items():
        target = output_dir / f"{name}.pdf"
        if not download:
            print(f"{name}: {url} -> {target}")
            continue
        try:
            urllib.request.urlretrieve(url, target)
            print(f"Downloaded {target}")
        except Exception as exc:  # noqa: BLE001
            print(f"Failed to download {url}: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw_pdfs"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    fetch_corpus(args.output_dir, download=args.download)


if __name__ == "__main__":
    main()
