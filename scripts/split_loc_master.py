#!/usr/bin/env python3
"""
split_loc_master.py
──────────────────
Distributes translations from `_upstream/<loc_language_code>/localisation/localisation.loc.tsv`
into separate files  `_upstream/<loc_language_code>/origin/text/db/*.loc.tsv`.

• **Why:** localisation of the game is stored "all together
  in localisation.loc.tsv, and for ease of editing, it is necessary to have
  the same structure as in EN / <language_you_are_translating_into> (by db files).

• **What it does:**
  1. Read master-файл localisation → vocabulary key → text_loc.
  2. Scans ALL files from `_upstream/en/text/db/*.loc.tsv`
     ─ They determine which localisation file the translation should go to.
  3. For each 'key' that already exists in the corresponding
     `_upstream/<loc_language_code>/origin/text/db/<file>` (or the file does not yet exist) :
       • if the localised translation exists in the master
       • and in the localised file the line is still English / empty
       → substitutes localised text.
  4. If the LOC-file does not yet exist, it creates a copy of the EN file and immediately
     substitutes translations.

*The service string `#Loc;...` and empty `key` are not changed.*
"""

import sys
from pathlib import Path
import pandas as pd

ROOT_EN     = Path("_upstream/en/text/db")
ROOT_LOC_DB  = Path("_upstream/<loc_language_code>/origin/text/db")
LOC_MASTER   = Path("_upstream/<loc_language_code>/localisation/localisation.loc.tsv")

def load(p: Path) -> pd.DataFrame:
    return pd.read_csv(
        p, sep="\t", dtype=str,
        keep_default_na=False, na_filter=False
    )

# ── 1. master-vocabulary ────────────────────────────────────────────────
if not LOC_MASTER.exists():
    sys.exit("⛔  _upstream/<loc_language_code>/localisation/localisation.loc.tsv not found.")

master_df = load(LOC_MASTER)
loc_master = dict(zip(master_df["key"], master_df["text"]))

# ── 2. list of EN files as a structure reference ─────────────────────────
targets = [p.name for p in ROOT_EN.glob("*.loc.tsv")]

def process(fname: str) -> None:
    path_en  = ROOT_EN   / fname
    path_loc  = ROOT_LOC_DB / fname

    if not path_en.exists():
        print(f"⚠️  {fname}: no EN reference, skip.")
        return

    en_df = load(path_en)

    # if there is no LOC-file, create a copy of the EN-file
    if path_loc.exists():
        loc_df = load(path_loc)
    else:
        path_loc.parent.mkdir(parents=True, exist_ok=True)
        loc_df = en_df.copy()

    # mask “can be edited”
    editable = (
            (loc_df["key"].str.strip() != "") &
            ~loc_df["key"].str.startswith("#Loc;")
    )

    updated = 0
    for idx in loc_df.index[editable]:
        k        = loc_df.at[idx, "key"]
        text_en  = en_df.at[idx, "text"]
        text_ru  = loc_master.get(k)
        text_cur = loc_df.at[idx, "text"]

        if text_ru and (text_cur == text_en or text_cur == "") and text_ru != text_en:
            loc_df.at[idx, "text"] = text_ru
            updated += 1

    if updated or not path_loc.exists():
        loc_df.to_csv(path_loc, sep="\t", index=False, na_rep="")
        print(f"✅ {fname}: updated {updated} lines.")
    else:
        print(f"–  {fname}: no update required.")

if __name__ == "__main__":
    for f in sys.argv[1:] or targets:
        process(f)
