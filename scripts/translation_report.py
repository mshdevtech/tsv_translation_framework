#!/usr/bin/env python3
"""
translation_report.py
• compare ORIGIN (_upstream/text/db) and TRANSLATION (translation/text/db)
• counts for each file: total, translated, untranslated
• displays a compact table
"""

from pathlib import Path
import sys, pandas as pd
from helpers import read_config

EXCLUSIONS = ["PLACEHOLDER", "placeholder", "text_rejected"]

def exclude_placeholders(df: pd.DataFrame) -> pd.DataFrame:
    return df[~df["text"].isin(EXCLUSIONS)]

def load(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, sep="\t", dtype=str, keep_default_na=False)

def main():
    rows = []
    grand_total, grand_done = 0, 0

    cfg = read_config()
    src_dir = cfg.upstream_db
    trg_dir = cfg.translation_db

    for src_path in sorted(src_dir.glob("*.loc.tsv")):
        trg_path = trg_dir / src_path.name

        # If the translation is not yet available, write 0%.
        if not trg_path.exists():
            rows.append((src_path.name, 0, 0, 0))
            continue

        src = load(src_path)
        trg = load(trg_path)

        # skip the empty key
        src = src[(src["key"].str.strip() != "") & (src["text"].str.strip() != "")]
        trg = trg[(trg["key"].str.strip() != "") & (trg["text"].str.strip() != "")]

        # skip the FIRST TWO service lines (index 0 and 1)
        src, trg = src.iloc[2:], trg.iloc[2:]

        # exclude placeholders
        src = exclude_placeholders(src)
        trg = exclude_placeholders(trg)

        # combine by key
        df = src.merge(trg[["key", "text"]], on="key", how="left",
                       suffixes=("_en", "_loc"))

        total = len(df)
        translated = (df["text_loc"] != df["text_en"]).sum()
        untranslated = total - translated
        rows.append((src_path.name, total, translated, untranslated))

        grand_total += total
        grand_done  += translated

    # 🔧 Guard when no source files were found (or nothing produced rows)
    if not rows:
        print("[INFO] No .loc.tsv files found in upstream directory:", src_dir)
        return 0

    # output
    col_w = max(len(name) for name, *_ in rows) + 2

    print(f"{'File'.ljust(col_w)}  Total  Done  Todo  %")
    for name, total, done, todo in rows:
        pct = 0 if total == 0 else round(done / total * 100)
        if pct < 100 and todo > 0:
            bar = "█" * (pct // 10)
            print(f"{name.ljust(col_w)}  {total:5}  {done:4}  {todo:4}  {pct:3}% {bar}")

    # general summary
    if grand_total:
        overall_pct = round(grand_done / grand_total * 100, 2)
        print("\n=== SUMMARY ===")
        print(f"Translated {grand_done} lines from {grand_total} "
              f"({overall_pct}% of the total).")
    else:
        print("\nNo data to count.")

if __name__ == "__main__":
    sys.exit(main())