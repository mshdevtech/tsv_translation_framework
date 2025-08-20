#!/usr/bin/env python3
"""
patch_lua.py
────────────────────────────
Inserts translated strings from TSV files into the selected Lua table.

Arguments (passed at runtime):
  --table   REGIONS_NAMES_LOCALISATION   # the name of the array in the Lua file
  --prefix  factions_screen_name         # TSV key prefix (add "_" + lua-key)

The logic of replacement:
 • searches for the rows inside the specified table like
       key = "Text"
       ["key"] = "Text"
 • generates a TSV key:   full_key =  f"{prefix}_{key}"   (if prefix = "")
                      ⇒ just takes `key`
 • if:
     – translation found in TSV for full_key
     – translation ≠ up1_text (if up1 is specified)
     – translation ≠ up2_text
   → Inserts new text into the Lua string.

The file is saved without backup (the original is in _upstream).
"""

import argparse, re, sys
from pathlib import Path
import pandas as pd
from helpers import read_config, add_project_root_arg, resolve_path

def main():
    # ── CLI arguments  ────────────────────────────────────────────────────
    ap = argparse.ArgumentParser(description="Insert translated strings from TSV files into Lua table.")
    add_project_root_arg(ap)
    ap.add_argument("--table", required=True, help="Lua table name")
    ap.add_argument("--prefix", default="", help="TSV key prefix (без _)")
    ap.add_argument("--lua-file", help="Path to Lua file (overrides .env)")
    ap.add_argument("--tr-dir", help="Translation TSV dir (overrides .env)")
    ap.add_argument("--up1-dir", help="First original TSV dir (overrides .env)")
    ap.add_argument("--up2-dir", help="Second original TSV dir (overrides .env)")
    args = ap.parse_args()

    cfg = read_config(args.project_root)
    path_lua = resolve_path(cfg.project_root, args.lua_file) if args.lua_file else cfg.patch_lua_file
    dir_db = resolve_path(cfg.project_root, args.tr_dir) if args.tr_dir else cfg.translation_db
    dir_up1 = resolve_path(cfg.project_root, args.up1_dir) if args.dir_up1 else cfg.dir_up1
    dir_up2 = resolve_path(cfg.project_root, args.up2_dir) if args.dir_up2 else cfg.dir_up2

    if not (path_lua.exists() and dir_db.exists() and dir_up2.exists()):
        sys.exit("⛔  These paths do not exist.")

    # ── read TSV → translation / source vocabularies  ───────────────────
    def load_dir(p: Path) -> dict[str, str]:
        d: dict[str,str] = {}
        for f in p.glob("*.loc.tsv"):
            df = pd.read_csv(f, sep="\t", dtype=str,
                             keep_default_na=False, na_filter=False)
            d.update(zip(df["key"], df["text"]))
        return d

    tr_dict   = load_dir(dir_db)
    up2_dict  = load_dir(dir_up2)
    up1_dict  = load_dir(dir_up1) if dir_up1 else {}

    # ── regex ────────────────────────────────────────────────────────
    # 1) find the entire table you need
    table_re = re.compile(
        rf'^[ \t]*(?P<open>{re.escape(args.table)}\s*=\s*\{{)'  # open
        r'(?P<body>.*?)'                                               # body
        r'^[ \t]*(?P<close>\})'                                        # close
        , re.S | re.M
    )

    # 2) inside body: key / ["key"] = "Text"
    row_re = re.compile(
        r'(?P<lhs>(\[\s*"(?P<kq>[^"]+)"\s*\])|(?P<kp>[A-Za-z0-9_]+))\s*=\s*"(?P<txt>[^"]*)"'
    )

    lua_text = path_lua.read_text(encoding="utf-8")

    def patch_body(body: str) -> tuple[str,int]:
        """Returns the modified body and the number of real updates."""
        updated = 0

        def repl(m: re.Match) -> str:
            nonlocal updated
            lua_key = m["kq"] or m["kp"]
            full_key = f"{args.prefix}_{lua_key}" if args.prefix else lua_key

            new = tr_dict.get(full_key)
            if not new:
                return m.group(0)

            # skip if new == any of the originals
            if new == up2_dict.get(full_key, ""):
                return m.group(0)
            if dir_up1 and new == up1_dict.get(full_key, ""):
                return m.group(0)

            updated += 1
            return f'{m["lhs"]} = "{new}"'

        new_body = row_re.sub(repl, body)
        return new_body, updated

    def patch_lua(src: str) -> tuple[str,int]:
        total_updates = 0

        def table_repl(t: re.Match) -> str:
            nonlocal total_updates
            original_body = t.group('body')
            patched_body, n = patch_body(original_body)
            total_updates += n
            # Let's put it back together: open + new body + close
            return f"{t.group('open')}{patched_body}{t.group('close')}"

        new_src = table_re.sub(table_repl, src, count=1)
        return new_src, total_updates

    patched, n = patch_lua(lua_text)

    if n:
        path_lua.write_text(patched, encoding="utf-8")
        print(f"✅  {path_lua.name}: replaced {n} lines in table {args.table}.")
    else:
        print(f"–  {path_lua.name}: no translated lines for {args.table} found.")

if __name__ == "__main__":
    main()
