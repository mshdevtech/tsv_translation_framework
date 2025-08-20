#!/usr/bin/env python3
"""
merge_patch_translation.py
──────────────────────────
• Goal: this script supplements text/db/<file> with completed translations from
  `_upstream/<loc_language_code>/text/db/<file>`, but **only** where, the translation in
  the main file has not yet been done (the line still matches the original
  `_upstream/en/db/<file>` or is empty).

Algorithm for each *.loc.tsv:
1. Read
      _upstream/en/db/XXX.loc.tsv   → en
      text/db/XXX.loc.tsv           → loc_main
      _upstream/<loc_language_code>/text/db/XXX.loc.tsv (if exists) → loc_patch
2. Skip rows with empty key and the first two service records
3. For each key present in loc_main:
      if  (loc_main.text == en.text)   or (loc_main.text == "")
      and     key exists in loc_main
      and     loc_main.text != en.text
      →     copy loc_main.text into loc_main.text
4. Save the file without changing the order of rows.
"""

import sys, os
from pathlib import Path
import pandas as pd

# Ensure the script can import from the current directory
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from helpers import load_env, resolve_path

PROJECT_ROOT = Path(".").resolve()

UPSTREAM_DB = os.environ.get("UPSTREAM_DB")
PATCH_DB = os.environ.get("PATCH_DB")
TRANSLATION_DB = os.environ.get("TRANSLATION_DB")

ROOT_EN     = resolve_path(PROJECT_ROOT, UPSTREAM_DB)
ROOT_PATCH  = resolve_path(PROJECT_ROOT, PATCH_DB)
ROOT_MAIN   = resolve_path(PROJECT_ROOT, TRANSLATION_DB)

def load(p: Path) -> pd.DataFrame:
    """We read TSV, we don't convert anything to NaN."""
    return pd.read_csv(
        p, sep="\t", dtype=str,
        keep_default_na=False, na_filter=False
    )

def process(file_name: str) -> None:
    path_en    = ROOT_EN   / file_name
    path_patch = ROOT_PATCH / file_name
    path_main  = ROOT_MAIN / file_name

    if not (path_en.exists() and path_main.exists() and path_patch.exists()):
        print(f"⚠️  Skip {file_name} — the file is not found in all three directories.")
        return

    en    = load(path_en)
    main  = load(path_main)
    patch = load(path_patch)

    # ── filters, but now we make *copies*, the main DF remains full
    sub_en    = en[  en["key"].str.strip()   != ""].iloc[1:]
    sub_main  = main[main["key"].str.strip() != ""].iloc[1:]
    sub_patch = patch[patch["key"].str.strip() != ""].iloc[1:]

    # we perform a quick lookup by key.
    en_lookup    = dict(zip(sub_en["key"],    sub_en["text"]))
    patch_lookup = dict(zip(sub_patch["key"], sub_patch["text"]))

    updated = 0
    for idx, row in main.iterrows():
        k = row["key"]
        text_main   = main.at[idx, "text"]        # take from the FULL DF
        text_en     = en_lookup.get(k, "")
        text_patch  = patch_lookup.get(k)

        if (
                k and text_patch and text_patch != text_en and
                (text_main == text_en or text_main == "")
        ):
            main.at[idx, "text"] = text_patch
            updated += 1

    if updated:
        main.to_csv(path_main, sep="\t", index=False, na_rep="")
        print(f"✅ {file_name}: updated {updated} lines.")
    else:
        print(f"–  {file_name}: no translations required.")

if __name__ == "__main__":
    targets = sys.argv[1:] or [p.name for p in ROOT_PATCH.glob("*.loc.tsv")]
    for fname in targets:
        process(fname)
