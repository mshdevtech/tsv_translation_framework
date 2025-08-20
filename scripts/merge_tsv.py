#!/usr/bin/env python3
"""
merge_tsv.py
────────────
This script merges (updates) translation files with the original.

What it does:
  - Adds new keys from the original (EN) to the corresponding translation files
  - Does not overwrite already translated lines
  - Archives deleted keys in the obsolete folder
  - Validates the structure and uniqueness of keys in the TSV

How to run:
  python scripts/merge_tsv.py

Purpose:
  - To ensure the translation always contains all current keys from the original
  - To avoid losing already completed translations
  - For convenient updating after the original files are updated
"""

import argparse, csv, sys, os
import pandas as pd
from pathlib import Path

# Ensure the script can import from the current directory
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from helpers import load_env, resolve_path

# ── Validation functions ─────────────────────────────────────────────────
def validate_tsv_file(file_path: Path) -> tuple[bool, list[str]]:
    """Validates one TSV file and returns (is_valid, error_messages)."""
    errors = []
    try:
        df = pd.read_csv(file_path, sep="\t", dtype=str, keep_default_na=False, quoting=csv.QUOTE_NONE, encoding_errors='ignore')
    except Exception as e:
        errors.append(f"failed to read file ({e})")
        return False, errors

    # Checking the columns
    required_cols = ["key", "text", "tooltip"]
    if list(df.columns) != required_cols:
        errors.append(f"columns are expected {required_cols}, but received {list(df.columns)}")
        return False, errors

    # Empty keys
    empty_rows = df["key"].str.strip() == ""
    if empty_rows.any():
        rows = ", ".join(map(str, (df.index[empty_rows] + 2)))  # +2: header + 0-based
        errors.append(f"empty key in the strings {rows}")

    # Duplicate keys
    non_empty_keys = df.loc[~empty_rows, "key"]
    dup_keys = non_empty_keys[non_empty_keys.duplicated()]
    if not dup_keys.empty:
        keys = ", ".join(dup_keys.unique())
        errors.append(f"key duplicates: {keys}")

    return len(errors) == 0, errors

def validate_directory(dir_path: Path, dir_name: str) -> tuple[bool, dict[str, list[str]]]:
    """Validates all TSV files in the directory and returns (is_valid, file_errors)."""
    print(f"🔍 Check the TSV in {dir_name} ({dir_path})...")
    
    if not dir_path.exists():
        print(f"⚠️  Directory {dir_name} does not exist")
        return True, {}
    
    file_errors = {}
    has_errors = False
    
    for file_path in sorted(dir_path.glob("*.loc.tsv")):
        is_valid, errors = validate_tsv_file(file_path)
        if errors:
            file_errors[file_path.name] = errors
            has_errors = True
            print(f"❌ {file_path.name}:")
            for error in errors:
                print(f"   • {error}")
        else:
            pass
    
    print()
    return not has_errors, file_errors

def ask_continue() -> bool:
    """Asks the user whether to continue execution."""
    while True:
        response = input("Continue merging? (y/n): ").lower().strip()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please enter 'y' or 'n'")

def main():
    ap = argparse.ArgumentParser(description="Merge upstream TSVs into translation TSVs for a subproject.")
    ap.add_argument("--project-root", default=".", help="Subproject root (default: .)")
    args = ap.parse_args()

    project_root = Path(args.project_root).resolve()
    env_file = project_root / ".env"
    load_env(env_file)


    upstream_db = os.environ.get("UPSTREAM_DB")
    translation_db = os.environ.get("TRANSLATION_DB")
    obsolete_dir = os.environ.get("OBSOLETE_DIR")

    src_dir = resolve_path(project_root, upstream_db)
    trg_dir = resolve_path(project_root, translation_db)
    obs_dir = resolve_path(project_root, obsolete_dir)

    files_done = total_added = total_removed = total_modified = 0

    # ── Checking files before merge ──────────────────────────────────
    print("=== PRELIMINARY VERIFICATION OF FILES ===\n")

    src_valid, src_errors = validate_directory(src_dir, "SRC_DIR")
    trg_valid, trg_errors = validate_directory(trg_dir, "TRG_DIR")

    if not src_valid or not trg_valid:
        print("⚠️  ERRORS FOUND IN FILES!")
        print("The script may not work correctly and it is better to fix the problem files yourself.")
        print()

        if not ask_continue():
            print("Merge canceled.")
            sys.exit(1)

        print("Continuing merge...\n")
    else:
        print("✅ All files are valid, proceeding.\n")

    print("=== STARTING THE MERGE ===\n")

    files_with_changes = 0

    for src_path in src_dir.glob("*.loc.tsv"):
        trg_path = trg_dir / src_path.name
        read = lambda p: pd.read_csv(
            p, sep="\t", dtype=str, keep_default_na=False, na_filter=False,
            quoting=csv.QUOTE_NONE, encoding_errors='ignore'
        )

        src = read(src_path)
        trg = read(trg_path) if trg_path.exists() else pd.DataFrame(columns=src.columns)

        # - Filter empty keys -
        src = src[src["key"].str.strip() != ""].copy()
        trg = trg[trg["key"].str.strip() != ""].copy()

        # - Merging -
        merged = src.merge(trg, on="key", how="left", suffixes=("", "_old"))

        # 1) if translation already exist — keep it
        # 2) if translation doesn't exist — copy original text
        merged["text"] = merged["text_old"].where(
            merged["text_old"].notna() & (merged["text_old"] != ""),        # if 'text_old' is not NaN → leave it
            merged["text"]                                                  # otherwise we take the value from 'text'
        )

        # - Count actually modified rows (where translation appeared or changed) -
        modified_count = 0
        if "text_old" in merged.columns:
            modified_mask = (merged["text"].notna()) & (merged["text"] != "") & (
                merged["text_old"].isna() | (merged["text_old"] == "") | (merged["text"] != merged["text_old"]))
            modified_count = modified_mask.sum()
        total_modified += modified_count

        merged = merged[src.columns]   # return column order

        # NaN → ""
        merged = merged.fillna("")

        trg_path.parent.mkdir(parents=True, exist_ok=True)

        # Save with pandas to_csv using QUOTE_NONE
        merged.to_csv(trg_path, sep='\t', index=False, quoting=csv.QUOTE_NONE, encoding='utf-8')

        # - statistic for new keys -
        new_keys = src.loc[~src["key"].isin(trg["key"])]
        total_added += len(new_keys)

        # -︎ Removed keys -
        removed = trg.loc[~trg["key"].isin(src["key"])]
        if not removed.empty:
            obs_dir.mkdir(parents=True, exist_ok=True)

            # Save the archive file with pandas to_csv
            archive_path = obs_dir / src_path.name
            removed.to_csv(archive_path, sep='\t', index=False, quoting=csv.QUOTE_NONE, encoding='utf-8')

            total_removed += len(removed)

        files_done += 1
        if len(new_keys) > 0 or len(removed) > 0 or modified_count > 0:
            print(f"✓ {src_path.name}: +{len(new_keys)} new, -{len(removed)} removed, ~{modified_count} modified")
            files_with_changes += 1

    if files_with_changes == 0:
        print("✅ All files are up to date")

    print("\n=== Merge completed ===")
    print(f"Processed files : {files_done}")
    print(f"New keys added  : {total_added}")
    print(f"Keys archived   : {total_removed}")
    print(f"Rows modified   : {total_modified}")
    print("Done!")

    sys.exit(0)

if __name__ == "__main__":
    main()