#!/usr/bin/env python3
"""Download all GIS source data for Mozambique.

Auto-downloads datasets with direct URLs.
Prints instructions for datasets requiring manual download or registration.

Usage:
    python 01_download_gis_data.py
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from config import DOWNLOAD_DIR, SOURCES  # type: ignore[import-untyped]


def download_file(url: str, dest: Path) -> bool:
    if dest.exists():
        print(f"  [skip] Already exists: {dest.name} ({dest.stat().st_size / 1e6:.1f} MB)")
        return True

    print(f"  [download] {url}")
    print(f"             → {dest.name}")
    try:
        urllib.request.urlretrieve(url, dest, reporthook=_progress)
        print(f"\n  [ok] {dest.stat().st_size / 1e6:.1f} MB")
        return True
    except Exception as e:
        print(f"\n  [error] {e}")
        return False


def _progress(block_num: int, block_size: int, total_size: int):
    downloaded = block_num * block_size
    if total_size > 0:
        pct = min(downloaded / total_size * 100, 100)
        bar = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        sys.stdout.write(f"\r  [{bar}] {pct:.0f}%")
        sys.stdout.flush()


def main():
    print("=" * 60)
    print("Moz GIS Data Download")
    print("=" * 60)

    auto_ok = 0
    auto_fail = 0
    manual_needed = []

    for key, source in SOURCES.items():
        print(f"\n--- {key}: {source['description']} ---")
        dest = DOWNLOAD_DIR / source["filename"]

        if source.get("manual"):
            if dest.exists():
                print(f"  [ok] Already downloaded: {dest.name}")
                auto_ok += 1
            else:
                print(f"  [manual] Requires manual download:")
                print(f"           {source['instructions']}")
                print(f"           Save to: {dest}")
                manual_needed.append(key)
        else:
            if download_file(source["url"], dest):
                auto_ok += 1
            else:
                auto_fail += 1

    print("\n" + "=" * 60)
    print(f"Results: {auto_ok} OK, {auto_fail} failed, {len(manual_needed)} manual")

    if manual_needed:
        print(f"\nManual downloads needed ({len(manual_needed)}):")
        for key in manual_needed:
            s = SOURCES[key]
            print(f"  - {key}: {s['instructions']}")
            print(f"    Save to: {DOWNLOAD_DIR / s['filename']}")

    if auto_fail:
        print(f"\n{auto_fail} automatic downloads failed. Re-run to retry.")

    print("\nNext step: python 02_harmonize_rasters.py")


if __name__ == "__main__":
    main()
