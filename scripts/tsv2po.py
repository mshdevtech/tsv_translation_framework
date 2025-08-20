#!/usr/bin/env python3
"""
tsv2po.py
─────────
Converts TSV files of the key | text | tooltip type into a standard GNU PO.

Operation mode
=============

• **single file**
  (the output PO will be next to the output-TSV, but with the .po extension)

      python tsv2po.py \
          --src  _upstream/en/text/db/names.loc.tsv \
          --trg  text/db/names.loc.tsv

• **in bulk - two folders**
  (PO files will be moved to the third folder, the structure and names will be preserved)

      python tsv2po.py \
          --srcdir _upstream/en/text/db \
          --trgdir text/db \
          --outdir _tmp
"""

import argparse, datetime
from pathlib import Path
import pandas as pd
from helpers import read_config, add_project_root_arg, resolve_path

# ── CLI ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    add_project_root_arg(ap)
    ap.add_argument("--src", help="original TSV")
    ap.add_argument("--trg", help="TSV with translation")
    ap.add_argument("--srcdir", help="source directory with TSVs")
    ap.add_argument("--trgdir", help="directory with translated TSVs")
    ap.add_argument("--outdir", default="po", help="where to put the po-files")
    args = ap.parse_args()

    cfg = read_config(args.project_root)

    # ── Escaping characters ───────────────────────────────────────────────
    def po_escape(txt: str) -> str:
        """Escapes characters, which make break PO."""
        if not txt:                       # None or ""
            return ""
        return (
            txt.replace("\\", "\\\\")   # backslash first
            .replace('"', r'\"')     # then quotation marks
        )


    # ── TSV → DataFrame reading utility ──────────────────────────────────
    def read_tsv(p: Path) -> pd.DataFrame:
        return pd.read_csv(
            p, sep="\t", dtype=str,
            names=["key", "text", "tooltip"],
            header=0, keep_default_na=False, na_filter=False,
            engine="python", on_bad_lines="skip"
        )

    # ── PO header ─────────────────────────────────────────────────────
    def po_header(filename: str) -> str:
        today = datetime.date.today().strftime("%Y-%m-%d")
        return (
            'msgid ""\n'
            'msgstr ""\n'
            '"Project-Id-Version: TSV-to-PO\\n"\n'
            f'"POT-Creation-Date: {today}\\n"\n'
            '"Language: uk\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            f'"X-Source-File: {filename}\\n"\n\n'
        )

    # ── function of converting DataFrame to PO-text ─────────────────────────
    def df_to_po(src_df: pd.DataFrame, trg_df: pd.DataFrame, src_name: str) -> str:
        src_map = dict(zip(src_df["key"], src_df["text"]))
        trg_map = dict(zip(trg_df["key"], trg_df["text"]))

        lines = [po_header(src_name)]
        for k, src_txt in src_map.items():
            tr_txt = trg_map.get(k, "")
            # skip service and empty keys
            if not k or k.startswith("#Loc;"):
                continue

            msgid = po_escape(src_txt)
            msgstr = po_escape(trg_map.get(k, ""))

            lines.append(f'msgctxt "{k}"')
            lines.append(f'msgid "{msgid}"')
            lines.append(f'msgstr "{msgstr}"\n')
        return "\n".join(lines)

    # ── single file converter ───────────────────────────────────────────
    def convert_single(src: Path, trg: Path, out: Path):
        src_df, trg_df = read_tsv(src), read_tsv(trg)
        po_text = df_to_po(src_df, trg_df, src.name)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(po_text, encoding="utf-8")
        # ― neat path output ―
        try:
            shown = out.relative_to(Path.cwd())
        except ValueError:
            shown = out
        print(f"✅  {shown}")

    # ── main logic ───────────────────────────────────────────────────
    if args.src and args.trg:
        src = resolve_path(cfg.project_root, args.src)
        trg = resolve_path(cfg.project_root, args.trg)
        out_path = trg.with_suffix(".po")
        convert_single(src, trg, out_path)
    elif args.srcdir and args.trgdir:
        srcdir = resolve_path(cfg.project_root, args.srcdir)
        trgdir = resolve_path(cfg.project_root, args.trgdir)
        outdir = resolve_path(cfg.project_root, args.outdir)
        if not (srcdir.exists() and trgdir.exists()):
            raise SystemExit("⛔  srcdir / trgdir do not exist.")
        for src_file in srcdir.glob("*.loc.tsv"):
            trg_file = trgdir / src_file.name
            if not trg_file.exists():
                print(f"⚠️  skipped {src_file.name} (no translation)")
                continue
            out_file = outdir / f"{src_file.stem}.po"
            convert_single(src_file, trg_file, out_file)
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
