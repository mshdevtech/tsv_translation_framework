#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
YAML="$ROOT/repos.yaml"

mkdir -p "$ROOT/translation"
cd "$ROOT/translation"

# Emit: name<TAB>url<TAB>branch  (branch defaults to "main")
yq -r '.repos[] | [.name, .url, (.branch // "main")] | @tsv' "$YAML" \
| while IFS=$'\t' read -r name url branch; do
  if [[ -z "${name:-}" || -z "${url:-}" ]]; then
    echo "[skip] invalid entry (name or url missing)"; continue
  fi

  if [[ -d "$name/.git" ]]; then
    echo "[update] $name"
    git -C "$name" fetch --all --prune
    git -C "$name" checkout "$branch"
    git -C "$name" pull --ff-only origin "$branch"
  else
    echo "[clone]  $name from $url ($branch)"
    git clone --branch "$branch" "$url" "$name"
  fi
done

echo "[done]"
