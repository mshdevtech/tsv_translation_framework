#!/usr/bin/env python3
"""
unescape_quotes.py
──────────────────
• Removes escaping like "" in column 'text':
    "Translated ""some word"" string" → Translated "some word" string
• Removes unnecessary outer brackets if the entire contents of the field were enclosed in "…".
• Does not change other columns, row order, or service rows.

Usage:
    # 1) By default, go through all *.loc.tsv files in text/db
    python unescape_quotes.py

    # 2) Specify file(s) or directory(s)
    python unescape_quotes.py text/db/names.loc.tsv
    python unescape_quotes.py text/db  other_dir/
"""

from pathlib import Path
import sys
import pandas as pd
import argparse
from helpers import read_config, add_project_root_arg, resolve_path

# Completely disable any "quoting" when reading/writing
QUOTE_NONE = 3         # equivalent csv.QUOTE_NONE (without importing csv)
QUOTECHAR  = "\x00"    # «impossible» character — to be "perceived as ordinary

def unescape_field(s: str):
    if not isinstance(s, str):
        return s
    # if the field is completely wrapped in quotation marks - remove them once
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    # remove the double quotes inside
    if '""' in s:
        # two passes guarantee processing of sequences like """" → ""
        s = s.replace('""', '"')
        while '""' in s:
            s = s.replace('""', '"')
    return s

def process_file(path: Path) -> int:
    df = pd.read_csv(
        path, sep="\t", dtype=str,
        keep_default_na=False, na_filter=False,
        engine="python", quoting=QUOTE_NONE, quotechar=QUOTECHAR
    )
    if "text" not in df.columns:
        print(f"{path.name}: the 'text' column was not found - skip.")
        return 0

    before = df["text"].copy()
    df["text"] = df["text"].map(unescape_field)
    changed = (df["text"] != before).sum()

    if changed:
        df.to_csv(
            path, sep="\t", index=False, na_rep="",
            quoting=QUOTE_NONE, quotechar=QUOTECHAR,
        )
    print(f"{path.name}: updated {changed} lines")
    return changed

def main():
    ap = argparse.ArgumentParser(description="Unescape quotes in translation TSV files.")
    add_project_root_arg(ap)
    ap.add_argument("paths", nargs="*", help="Files or directories to process (default: text/db)")
    args = ap.parse_args()

    cfg = read_config(args.project_root)

    files: list[Path] = []
    if args.paths:
        for a in args.paths:
            p = resolve_path(cfg.project_root, a)
            if p.is_dir():
                files.extend(sorted(p.glob("*.loc.tsv")))
            else:
                files.append(p)
    else:
        files = sorted(cfg.translation_db.glob("*.loc.tsv"))

    if not files:
        print("No files found.")
        sys.exit(1)

    total = 0
    for f in files:
        if f.exists():
            total += process_file(f)
        else:
            print(f"{f} — not found, skip.")
    print(f"Done. Total number of rows changed: {total}")

if __name__ == "__main__":
    main()
