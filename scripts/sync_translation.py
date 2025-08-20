"""
sync_translation.py
───────────────────
Syncs a project's translation directory into the target mod directory (DST).

Defaults assume you're running it from the framework, pointing at a subproject:
  python scripts/sync_translation.py --project-root translation/<project>

What it does:
  - Copies all files and folders from translation/<project> into the specified target folder (DST)
  - Before copying, deletes only those subfolders/files in DST that exist in translation (does not touch other files, such as .git)
  - If the target folder does not exist — displays a hint to the user

How to run:
  python scripts/sync_translation.py --project-root translation/<project>             # from framework root
  python scripts/sync_translation.py --project-root translation/<project> --dry-run   # preview
  (or automatically via git pre-commit hook, see README)

Purpose:
  - To quickly update translation files in the mod folder for in-game testing
  - To avoid errors caused by outdated or unnecessary files

CLI:
  --project-root PATH   Subproject root (default: CWD)
  --src NAME            Source subdir under project root (default: "")
  --dst PATH            Destination override (else read DST from .env)
  --dry-run             Print actions only
"""
import argparse
import os
import shutil
import sys
from pathlib import Path
from helpers import add_project_root_arg, read_config, resolve_path

IGNORE_NAMES = {
    ".git", ".gitignore", ".gitattributes", ".gitmodules",
    ".env", ".pre-commit-config.yaml", 'run',
    ".DS_Store", "Thumbs.db",
}
IGNORE_SUFFIXES = (".tmp", ".bak", ".swp", "~")

def should_ignore(name: str) -> bool:
    return name in IGNORE_NAMES or name.endswith(IGNORE_SUFFIXES)

def clear_folder(dst: Path, src: Path, dry_run: bool = False):
    """Delete only those entries in dst that also exist in src (protects other files like .git)."""
    for name in os.listdir(src):
        src_path = src / name
        dst_path = dst / name
        if dst_path.exists():
            if src_path.is_dir() and dst_path.is_dir():
                # Remove the whole subtree to avoid stale files
                if dry_run:
                    print(f"[dry-run] rmtree {dst_path}")
                else:
                    shutil.rmtree(dst_path)
                    print(f"Deleted folder: {dst_path}")
            elif src_path.is_file() and dst_path.is_dir():
                if dry_run:
                    print(f"[dry-run] rmtree {dst_path} (dir replaced by file)")
                else:
                    shutil.rmtree(dst_path)
                    print(f"Deleted folder (instead of file): {dst_path}")

def copytree(src: Path, dst: Path, dry_run: bool = False):
    print(f"Copying from {src} to {dst}")
    for item in os.listdir(src):
        if should_ignore(item): continue
        s = src / item
        d = dst / item
        if s.is_dir():
            if dry_run:
                print(f"[dry-run] copytree {s} -> {d}")
            else:
                shutil.copytree(s, d, dirs_exist_ok=True)
                print(f"Copied folder: {s} -> {d}")
        else:
            if dry_run:
                print(f"[dry-run] copy2 {s} -> {d}")
            else:
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                print(f"Copied file: {s} -> {d}")

def main():
    ap = argparse.ArgumentParser(description="Sync project translation into target directory.")
    add_project_root_arg(ap)
    ap.add_argument("--src", "-s", default=".", help='Source subdir under project root (default: ".")')
    ap.add_argument("--dst", "-d", help="Destination path (overrides DST in .env)")
    ap.add_argument("--dry-run", action="store_true", help="Print actions, do not modify files")
    args = ap.parse_args()

    cfg = read_config(args.project_root)

    src = resolve_path(cfg.project_root, args.src) if args.src else cfg.translation_db.parent
    dst = resolve_path(cfg.project_root, args.dst) if args.dst else cfg.dst

    print(f"Project root: {cfg.project_root}")
    print(f"SRC: {src}")
    print(f"DST: {dst if dst else '(unset)'}")

    if not src.exists():
        print(f"[ERROR] Source folder does not exist: {src}", file=sys.stderr)
        sys.exit(1)

    if not dst:
        print("[ERROR] 'DST' not set. Provide --dst or set DST in the project's .env.", file=sys.stderr)
        sys.exit(1)

    if not dst.exists():
        print(f"[ERROR] Target folder does not exist: {dst}\nCreate it or change DST.", file=sys.stderr)
        sys.exit(1)

    clear_folder(dst, src, dry_run=args.dry_run)
    copytree(src, dst, dry_run=args.dry_run)
    print(f"Synchronization {'(dry-run) ' if args.dry_run else ''}completed: {src} -> {dst}")

if __name__ == "__main__":
    main()