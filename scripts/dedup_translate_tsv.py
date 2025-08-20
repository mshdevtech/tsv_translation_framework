#!/usr/bin/env python3
"""
dedup_translate_tsv.py
──────────────────────
The script has **two actions**:

1.  extract  –  makes the *dedup* of the original TSV
2.  apply    –  returns translations from the "_dedup" file back to the source file

────────────
Usage
────────────

# 1) Create a file for translation without duplicates
python dedup_translate_tsv.py extract path/to/names.loc.tsv

# 2) After editing the "translate" column, apply the translation
python dedup_translate_tsv.py apply   _dedup/names.loc._dedup.tsv \
                               path/to/names.loc.tsv

────────────
The format of the _dedup file
────────────
| text | translate | keys |
|------|-----------|------|
| Alda |           | names_name_2147380140 |
| Cairo|           | att_reg_aegyptus_oxyrhynchus, … |

The **translate** column is edited by the translator.
The **keys** column is required by the script - do not change it.
"""

import sys, csv, pandas as pd
import argparse

from pathlib import Path
from helpers import read_config, add_project_root_arg, resolve_path

def extract(src: Path, dedup_dir: Path) -> None:
    df = pd.read_csv(src, sep="\t", dtype=str,
                     keep_default_na=False, na_filter=False)

    # group by 'text'
    g = df.groupby("text")["key"].agg(lambda k: ",".join(sorted(k)))
    dedup_df = (
        g.reset_index()
        .rename(columns={"key": "keys"})
        .assign(translate="")
        .loc[:, ["text", "translate", "keys"]]
    )

    out = dedup_dir / f"{src.stem}._dedup.tsv"
    dedup_df.to_csv(out, sep="\t", index=False, quoting=csv.QUOTE_NONE)
    try:
        shown = out.relative_to(Path.cwd())
    except ValueError:
        shown = out
    print(f"✅  Created {shown}")

def apply(dedup_file: Path, tsv_orig: Path) -> None:
    """Transfers the translation from the 'translate' column to the text of the original TSV,
       by searching for strings using the keys in the keys column."""
    dedup = pd.read_csv(dedup_file, sep="\t", dtype=str,
                        keep_default_na=False, na_filter=False)
    orig  = pd.read_csv(tsv_orig,  sep="\t", dtype=str,
                        keep_default_na=False, na_filter=False)

    # build a key → translate dictionary
    key2tr: dict[str, str] = {}
    for row in dedup.itertuples(index=False):
        if not row.translate:                 # translation is empty - skip
            continue
        for k in map(str.strip, row.keys.split(",")):
            if k:                             # skip empty elements
                key2tr[k] = row.translate

    if not key2tr:
        print("–  The dedup file does not have a filled translate column.")
        return

    # apply (only for those keys that exist in the dictionary)
    mask = orig["key"].isin(key2tr.keys())
    orig.loc[mask, "text"] = orig.loc[mask, "key"].map(key2tr)

    orig.to_csv(tsv_orig, sep="\t", index=False, quoting=csv.QUOTE_NONE)
    print(f"✅  Updated {tsv_orig.name}: translated {mask.sum()} lines.")

def main():
    ap = argparse.ArgumentParser(description="Deduplicate and apply translations in TSV files.")
    add_project_root_arg(ap)
    ap.add_argument("action", choices=["extract", "apply"], help="Action to perform: extract or apply")
    ap.add_argument("src", nargs="?", help="Source file for extract, or dedup file for apply")
    ap.add_argument("dst", nargs="?", help="Destination file for apply (original TSV)")
    args = ap.parse_args()

    cfg = read_config(args.project_root)
    temp_dir = cfg.temp_dir
    dedup_dir = temp_dir
    dedup_dir.mkdir(exist_ok=True)

    if args.action == "extract":
        if not args.src:
            print("Please specify the source TSV file for extraction.")
            sys.exit(1)
        extract(resolve_path(cfg.project_root, args.src), dedup_dir)
    elif args.action == "apply":
        if not args.src or not args.dst:
            print("Please specify the dedup TSV file and the destination TSV file for apply.")
            sys.exit(1)
        apply(resolve_path(cfg.project_root, args.src), resolve_path(cfg.project_root, args.dst))

if __name__ == "__main__":
    main()
