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

import sys
from pathlib import Path
import pandas as pd
import argparse

from helpers import read_config, add_project_root_arg, resolve_path

def load(p: Path) -> pd.DataFrame:
    """We read TSV, we don't convert anything to NaN."""
    return pd.read_csv(
        p, sep="\t", dtype=str,
        keep_default_na=False, na_filter=False
    )

def main():
    ap = argparse.ArgumentParser(description="Merge patch translations into main translation files.")
    add_project_root_arg(ap)
    args, extra = ap.parse_known_args()

    cfg = read_config(args.project_root)
    root_en = cfg.upstream_db
    root_patch = cfg.patch_db
    root_translation = cfg.translation_db

    if not root_patch:
        print("[ERROR] PATCH_DB not set in .env or arguments.")
        sys.exit(1)

    def process(file_name: str) -> None:
        path_en    = root_en   / file_name
        path_patch = root_patch / file_name
        path_translation  = root_translation / file_name

        if not (path_en.exists() and path_translation.exists() and path_patch.exists()):
            print(f"⚠️  Skip {file_name} — the file is not found in all three directories.")
            return

        en    = load(path_en)
        translation  = load(path_translation)
        patch = load(path_patch)

        # ── filters, but now we make *copies*, the main DF remains full
        sub_en    = en[  en["key"].str.strip()   != ""].iloc[1:]
        # sub_main  = translation[translation["key"].str.strip() != ""].iloc[1:]
        sub_patch = patch[patch["key"].str.strip() != ""].iloc[1:]

        # we perform a quick lookup by key.
        en_lookup    = dict(zip(sub_en["key"],    sub_en["text"]))
        patch_lookup = dict(zip(sub_patch["key"], sub_patch["text"]))

        updated = 0
        for idx, row in translation.iterrows():
            k = row["key"]
            text_main   = translation.at[idx, "text"]        # take from the FULL DF
            text_en     = en_lookup.get(k, "")
            text_patch  = patch_lookup.get(k)

            if (
                    k and text_patch and text_patch != text_en and
                    (text_main == text_en or text_main == "")
            ):
                translation.at[idx, "text"] = text_patch
                updated += 1

        if updated:
            translation.to_csv(path_translation, sep="\t", index=False, na_rep="")
            print(f"✅ {file_name}: updated {updated} lines.")
        else:
            print(f"–  {file_name}: no translations required.")

    targets = extra or [p.name for p in root_patch.glob("*.loc.tsv")]
    for fname in targets:
        process(fname)

if __name__ == "__main__":
    main()
