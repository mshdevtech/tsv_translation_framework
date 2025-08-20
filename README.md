# TSV Translation Framework

## Overview

The **TSV Translation Framework** is a toolkit for managing, updating, and synchronizing translation files (in TSV format) for game mods, especially those using the "loc.tsv" format (such as Total War modding). It provides scripts to validate, merge, deduplicate, synchronize, and report on translation progress, as well as utilities for working with Lua scripts and integrating with multiple repositories.

The framework is designed to:
- Keep translation files in sync with upstream (original) files.
- Help translators and modders efficiently manage large sets of localization data.
- Automate repetitive tasks and reduce the risk of errors.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Main Scripts & Usage](#main-scripts--usage)
- [Advanced Usage](#advanced-usage)
- [Contributing](#contributing)
- [License](#license)

---

## Project Structure

```
tsv_translation_framework/
├── scripts/                  # Main Python scripts for translation management
├── translation/              # Example translation projects
│   └── <project>/            # Each translation project (submod) lives here
│       └── text/db/          # Translation TSV files
├── example_subproject/       # Example subproject structure
├── repos.yaml.example        # Example config for multi-repo management
└── ...
```

---

## Setup & Installation

### Prerequisites

- **Python 3.8+** (recommended)
- **pip** (Python package manager)
- **pandas** Python library

### Install Python Dependencies

The main dependency is `pandas`. Install it with:

```bash
pip install pandas
```

If you use any scripts that require additional libraries, install them as needed.

### Clone the Repository

```bash
git clone <your_repo_url>
cd tsv_translation_framework
```

---

## Configuration

### Environment Variables

Some scripts use a `.env` file in your project or subproject root to override default paths (see `scripts/helpers.py` for all options). Example variables:

- `UPSTREAM_DB` - Path to original (EN) TSV files
- `TRANSLATION_DB` - Path to your translation TSV files
- `OBSOLETE_DIR` - Where to archive removed keys
- `DST` - Target mod directory for syncing files

### Multi-Repo Management

To manage multiple translation projects, copy `repos.yaml.example` to `repos.yaml` and fill in your repositories:

```yaml
repos:
  - name: my_mod
    url:  https://github.com/myuser/my_mod.git
    branch: main
```

Then use `scripts/sync_repos.sh` to clone or update all listed repos.

---

## Main Scripts & Usage

All scripts are in the `scripts/` directory. Run them with `python scripts/<script>.py [options]`.

### 1. **merge_tsv.py**
Merge upstream (original) TSVs into your translation files, adding new keys and archiving removed ones.

```bash
python scripts/merge_tsv.py --project-root translation/<project>
```

### 2. **validate_tsv.py**
Validate the structure of your TSV files (columns, duplicates, empty keys).

```bash
python scripts/validate_tsv.py --project-root translation/<project>
```

### 3. **sync_translation.py**
Sync your translation directory into the mod's target directory (for in-game testing).

```bash
python scripts/sync_translation.py --project-root translation/<project> --dst <mod_folder>
```
Add `--dry-run` to preview actions.

### 4. **split_loc_master.py**
Split a master localisation file into separate files by DB structure.

```bash
python scripts/split_loc_master.py --project-root translation/<project>
```

### 5. **dedup_translate_tsv.py**
Deduplicate translation strings for easier translation, then apply translations back.

```bash
# Extract deduplicated file
python scripts/dedup_translate_tsv.py extract path/to/names.loc.tsv

# Apply translations back
python scripts/dedup_translate_tsv.py apply _dedup/names.loc._dedup.tsv path/to/names.loc.tsv
```

### 6. **merge_patch_translation.py**
Merge completed translations from a patch directory into your main translation files.

```bash
python scripts/merge_patch_translation.py --project-root translation/<project>
```

### 7. **sync_lua_files.py**
Synchronize Lua scripts from upstream to your translation folder, only replacing existing files.

```bash
python scripts/sync_lua_files.py --project-root translation/<project>
```

### 8. **tsv2po.py**
Convert TSV files to GNU PO format for use with standard translation tools.

```bash
python scripts/tsv2po.py --src <original.tsv> --trg <translated.tsv>
```

### 9. **translation_report.py**
Generate a report of translation progress (total, translated, untranslated lines).

```bash
python scripts/translation_report.py --project-root translation/<project>
```

---

## Advanced Usage

### Multi-Repo Sync

- Edit `repos.yaml` (see `repos.yaml.example`).
- Run:

  ```bash
  bash scripts/sync_repos.sh
  ```

### Pre-commit Integration

You can automate translation syncs with a pre-commit hook. See `example_subproject/.pre-commit-config.yaml.example` for a template.

---

## Contributing

1. Fork the repository.
2. Create a new branch: `git checkout -b feature-name`
3. Make your changes.
4. Commit: `git commit -am "Add feature"`
5. Push: `git push origin feature-name`
6. Open a pull request.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Inspired by the needs of the Total War modding community.
- Thanks to all contributors and translators!

---

**For more details, see the docstrings in each script.**
