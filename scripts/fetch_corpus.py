"""Fetch or list candidate insurer PDFs for manual review."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import urllib.request


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


CORPUS_URLS = {
    "aami_home_contents": "https://www.aami.com.au/content/dam/assets/documents/aami/home/aami-home-contents-insurance-pds.pdf",
    "allianz_home_insurance": "https://www.einsure.com.au/wb/public/openPolicyDocument/POL1353DIR102420250114/%24FILE/POL1353DIR.pdf?open=",
    "budget_direct_home_contents": "https://www.budgetdirect.com.au/content/dam/budgetdirect/website-assets/documents/home-insurance/home-and-contents-pds.pdf",
    "coles_home_insurance": "https://www.coles.com.au/content/dam/coles/coles-financial-services/insurance/pdf/coles-home-insurance-pds-nov-2023.pdf",
    "nrma_home_insurance": "https://www.nrma.com.au/content/dam/insurance-brands-aus/nrma/au/en/documents/home/nrma-home-pds-nrmahompds-rev2-0923.pdf",
    "qbe_contents_insurance": "https://qmdocumentlibrary.qbe.com/getfile?revision=1E7CD841-5672-4A68-AB6B-39A16E0691A2",
    "racv_home_insurance": "https://www.racv.com.au/content/dam/racv-assets/documents/insurance/home-insurance/pds/home-insurance-pds-G018333-0421.pdf",
    "suncorp_home_contents": "https://www.suncorp.com.au/content/dam/suncorp/insurance/suncorp-insurance/documents/home-and-contents/home/suncorp-home-and-contents-pds-12314-24-05-25-a.pdf",
    "youi_home_insurance": "https://www.youi.com.au/documents/home-pds",
}


def fetch_corpus(output_dir: Path, *, download: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, url in CORPUS_URLS.items():
        target = output_dir / f"{name}.pdf"
        if not download:
            print(f"{name}: {url} -> {target}")
            continue
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "QuoteGuard/0.1 (corpus collection for local evaluation)",
                },
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                target.write_bytes(response.read())
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
