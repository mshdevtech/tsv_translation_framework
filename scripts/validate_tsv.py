#!/usr/bin/env python3
"""
validate_tsv.py – This script quickly checks all *.loc.tsv files in the specified folder or in text/db/

• 3 columns in order: key, text, tooltip
• key is not empty
• no duplicate keys
• TSV separator = \t

The tooltip column is not analyzed – the game needs it, but its content does not interest us.

Usage:
    python scripts/validate_tsv.py                    # checks text/db/
    python scripts/validate_tsv.py path/to/folder     # checks the specified folder
"""

from pathlib import Path
import sys, argparse
import pandas as pd
from helpers import read_config, add_project_root_arg, resolve_path

REQUIRED_COLS = ["key", "text", "tooltip"]
EXIT_CODE = 0
def fail(msg: str) -> None:
    """Adds a message and sets the exit code to 1."""
    global EXIT_CODE
    print(f"❌ {msg}")
    EXIT_CODE = 1

def warn(msg: str) -> None:
    global EXIT_CODE
    print(f"⚠️  {msg}")
    EXIT_CODE = 2


def main():
    # Determine the path to the folder to be checked
    ap = argparse.ArgumentParser(description="Validate TSV files in specified dir.")
    add_project_root_arg(ap)
    ap.add_argument("--dir", "-d", help='Specifies the directory to check')
    args = ap.parse_args()

    cfg = read_config(args.project_root)

    validate_dir = resolve_path(cfg.project_root, args.dir) if args.dir else cfg.translation_db
    print(f"🔍 Check the TSV in {validate_dir} …\n")

    for file in sorted(validate_dir.glob("*.loc.tsv")):
        try:
            df = pd.read_csv(file, sep="\t", dtype=str, keep_default_na=False)
        except Exception as e:
            fail(f"{file}: failed to read file ({e})")
            continue

        # 1. Check the columns
        if list(df.columns) != REQUIRED_COLS:
            fail(f"{file}: columns are expected {REQUIRED_COLS}, but received {list(df.columns)}")

        # 2. Empty key
        empty_rows = df["key"].str.strip() == ""
        if empty_rows.any():
            rows = ", ".join(map(str, (df.index[empty_rows] + 2)))  # +2: header + 0-based
            warn(f"{file}: empty key in the strings {rows}")

        # 3. Duplicate keys
        non_empty_keys = df.loc[~empty_rows, "key"]
        dup_keys = non_empty_keys[non_empty_keys.duplicated()]
        if not dup_keys.empty:
            keys = ", ".join(dup_keys.unique())
            fail(f"{file}: key duplicates: {keys}")

    # ── Summary ─────────────────────────────────────────────────────────────
    if EXIT_CODE == 1:
        print("\n❌ The check finished with errors.")
    elif EXIT_CODE == 2:
        print("\n⚠️ The check finished with warnings.")
    else:
        print("\n✅ All files are valid - no problems found.")

if __name__ == "__main__":
    sys.exit(main())