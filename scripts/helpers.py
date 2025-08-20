# scripts/helpers.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import argparse, os

# --- small utilities ---
def load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip().strip('"').strip("'")

def resolve_path(project_root: Path, value: str) -> Path:
    p = Path(value).expanduser()
    return p if p.is_absolute() else (project_root / p)

def resolve_opt(project_root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    return resolve_path(project_root, value)

def add_project_root_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project-root", "-p", default=".", help="Subproject root (default: .)")

# --- config model ---
@dataclass
class Config:
    project_root: Path
    env_file: Path
    upstream_db: Path          # e.g. _upstream/en/text/db
    translation_db: Path       # e.g. translation/text/db
    patch_db: Path | None      # optional
    obsolete_dir: Path         # e.g. _obsolete
    temp_dir: Path | None      # optional
    dir_up1: Path | None       # optional
    dir_up2: Path              # e.g. _upstream/en/text/db
    split_loc_file: Path       # used by patch_lua.py
    patch_lua_file: Path       # used by split_loc_master.py
    split_loc_dir: Path        # used by split_loc_master.py
    dst: Path | None           # used by sync_translation.py; optional

DEFAULTS = {
    "UPSTREAM_DB":    "_upstream/en/text/db",
    "TRANSLATION_DB": "translation/text/db",
    "OBSOLETE_DIR":   "_obsolete",
    "TEMP_DIR":       "_temp",
    "DIR_UP2":       "_upstream/en/text/db",
    "PATH_LUA_FILE":       "lua_scripts/frontend_strings.lua",
    # "DST":          (no default; usually per-user)
    # "PATCH_DB":     (optional)
}

def read_config(project_root: str | Path = ".", env_file: str | Path | None = None) -> Config:
    pr = Path(project_root).resolve()
    env = Path(env_file) if env_file else (pr / ".env")
    load_env(env)

    def getv(key: str, default_key: str | None = None) -> str | None:
        if key in os.environ:
            return os.environ[key]
        if default_key and default_key in DEFAULTS:
            return DEFAULTS[default_key]
        return None

    upstream_db    = resolve_path(pr, getv("UPSTREAM_DB", "UPSTREAM_DB"))
    translation_db = resolve_path(pr, getv("TRANSLATION_DB", "TRANSLATION_DB"))
    obsolete_dir   = resolve_path(pr, getv("OBSOLETE_DIR", "OBSOLETE_DIR"))
    patch_db       = resolve_opt(pr, getv("PATCH_DB"))
    temp_dir       = resolve_opt(pr, getv("TEMP_DIR", "TEMP_DIR"))
    dir_up1        = resolve_opt(pr, getv("DIR_UP1"))
    dir_up2        = resolve_opt(pr, getv("DIR_UP2", "DIR_UP2"))
    patch_lua_file = resolve_opt(pr, getv("PATH_LUA_FILE", "PATH_LUA_FILE"))
    split_loc_file = resolve_opt(pr, getv("SPLIT_LOC_FILE"))
    split_loc_dir  = resolve_opt(pr, getv("SPLIT_LOC_DIR"))
    dst            = resolve_opt(pr, getv("DST"))  # may be None; scripts can require it

    return Config(
        project_root=pr,
        env_file=env,
        upstream_db=upstream_db,
        translation_db=translation_db,
        patch_db=patch_db,
        obsolete_dir=obsolete_dir,
        temp_dir=temp_dir,
        dir_up1=dir_up1,
        dir_up2=dir_up2,
        patch_lua_file=patch_lua_file,
        split_loc_file=split_loc_file,
        split_loc_dir=split_loc_dir,
        dst=dst,
    )