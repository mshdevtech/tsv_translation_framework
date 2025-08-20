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

from pathlib import Path
import sys, csv, os, pandas as pd

from pathlib import Path

# Ensure the script can import from the current directory
THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from helpers import load_env, resolve_path

PROJECT_ROOT = Path(".").resolve()

env_file = PROJECT_ROOT / ".env"
load_env(env_file)

TEMP_DIR = os.environ.get("TEMP_DIR")

DEDUP_DIR = resolve_path(PROJECT_ROOT, TEMP_DIR)          # directory where _dedup-files are stored
DEDUP_DIR.mkdir(exist_ok=True)

def extract(src: Path) -> None:
    df = pd.read_csv(src, sep="\t", dtype=str,
                     keep_default_na=False, na_filter=False)

    # групуємо за text
    g = df.groupby("text")["key"].agg(lambda k: ",".join(sorted(k)))
    dedup_df = (
        g.reset_index()
        .rename(columns={"key": "keys"})
        .assign(translate="")
        .loc[:, ["text", "translate", "keys"]]
    )

    out = DEDUP_DIR / f"{src.stem}._dedup.tsv"
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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:\n"
              "  extract <src.tsv>\n"
              "  apply   <_dedup.tsv> <src.tsv>")
        sys.exit(1)

    action = sys.argv[1]
    if action == "extract" and len(sys.argv) == 3:
        extract(Path(sys.argv[2]))
    elif action == "apply" and len(sys.argv) == 4:
        apply(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        print("Wrong arguments.")
        sys.exit(1)
