#!/usr/bin/env python3
"""
Script to sync Lua files from _upstream/en to translation folder.
Only replaces existing files, reports deleted ones.

This script is designed for syncing translated Lua scripts with original ones from MK1212AD mod
that can be updated from time to time. It performs a safe sync by only replacing files
that already exist in the translation folder, preventing accidental overwrites.

USAGE EXAMPLES:
    # Basic usage - run from project root
    python scripts/sync_lua_files.py
    
    # Run from scripts directory
    cd scripts
    python sync_lua_files.py
    
    # Run with verbose output (if you want to see all skipped files)
    python scripts/sync_lua_files.py | tee sync_log.txt

WHAT IT DOES:
    1. Scans _upstream/en directory for all .lua files
    2. Scans translation directory for existing .lua files
    3. Copies upstream files to translation folder ONLY if they already exist there
    4. Reports files that were skipped (not in translation)
    5. Reports files that exist in translation but were deleted from upstream
    6. Provides a summary of all operations

SAFETY FEATURES:
    - Never creates new files in translation folder
    - Only overwrites existing files
    - Preserves file permissions and timestamps
    - Creates backup-friendly output for git diff review

AFTER RUNNING:
    - Review changes with: git diff
    - Check for any unexpected modifications
    - Commit changes if satisfied: git add . && git commit -m "Sync Lua files from upstream"
"""

import os
import shutil
import sys
from pathlib import Path
from typing import List, Tuple, Set

def find_lua_files(directory: Path) -> List[Path]:
    """
    Recursively find all .lua files in the given directory.
    
    Args:
        directory: Path object pointing to the directory to search
        
    Returns:
        List of Path objects for all .lua files found
    """
    lua_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.lua'):
                lua_files.append(Path(root) / file)
    return lua_files

def get_relative_path(file_path: Path, base_dir: Path) -> Path:
    """
    Get the relative path from base_dir to file_path.
    
    Args:
        file_path: Full path to the file
        base_dir: Base directory to calculate relative path from
        
    Returns:
        Relative path from base_dir to file_path
    """
    try:
        return file_path.relative_to(base_dir)
    except ValueError:
        return file_path

def sync_lua_files(upstream_dir: Path, translation_dir: Path) -> Tuple[int, int, List[str]]:
    """
    Sync Lua files from upstream to translation folder.
    
    This function performs the main sync operation:
    - Only copies files that already exist in translation folder
    - Skips files that don't exist in translation
    - Reports files that were deleted from upstream
    
    Args:
        upstream_dir: Path to _upstream/en directory
        translation_dir: Path to translation directory
        
    Returns:
        Tuple containing:
        - files_copied: Number of files successfully copied
        - files_skipped: Number of files skipped (not in translation)
        - deleted_files: List of files that exist in translation but not in upstream
    """
    # Validate input directories
    if not upstream_dir.exists():
        print(f"Error: Upstream directory {upstream_dir} does not exist!")
        return 0, 0, []
    
    if not translation_dir.exists():
        print(f"Error: Translation directory {translation_dir} does not exist!")
        return 0, 0, []
    
    # Find all Lua files in both directories
    print("Scanning directories for Lua files...")
    upstream_lua_files = find_lua_files(upstream_dir)
    print(f"Found {len(upstream_lua_files)} Lua files in {upstream_dir}")
    
    translation_lua_files = find_lua_files(translation_dir)
    translation_lua_set = {get_relative_path(f, translation_dir) for f in translation_lua_files}
    print(f"Found {len(translation_lua_files)} Lua files in {translation_dir}")
    
    # Initialize counters and tracking lists
    files_copied = 0
    files_skipped = 0
    deleted_files = []
    
    print("\nProcessing upstream files...")
    # Process each upstream Lua file
    for upstream_file in upstream_lua_files:
        relative_path = get_relative_path(upstream_file, upstream_dir)
        target_file = translation_dir / relative_path
        
        if target_file.exists():
            # File exists in translation, safe to copy
            try:
                # Ensure target directory exists (in case of nested structure changes)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy the file with metadata preservation
                shutil.copy2(upstream_file, target_file)
                print(f"✓ Copied: {relative_path}")
                files_copied += 1
            except Exception as e:
                print(f"✗ Error copying {relative_path}: {e}")
        else:
            # File doesn't exist in translation, skip it
            print(f"- Skipped (not in translation): {relative_path}")
            files_skipped += 1
    
    print("\nChecking for deleted files...")
    # Check for deleted files (files that exist in translation but not in upstream)
    upstream_lua_set = {get_relative_path(f, upstream_dir) for f in upstream_lua_files}
    for translation_file in translation_lua_files:
        relative_path = get_relative_path(translation_file, translation_dir)
        if relative_path not in upstream_lua_set:
            deleted_files.append(str(relative_path))
    
    return files_copied, files_skipped, deleted_files

def main():
    """
    Main function that orchestrates the sync process.
    
    This function:
    1. Sets up the directory paths
    2. Calls the sync function
    3. Displays a comprehensive summary
    4. Provides guidance for next steps
    """
    # Get script directory and project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define directories relative to project root
    upstream_dir = project_root / "_upstream" / "en"
    translation_dir = project_root / "translation"
    
    # Display script header and configuration
    print("Lua File Sync Script")
    print("=" * 50)
    print("Purpose: Sync Lua files from upstream to translation folder")
    print("Safety: Only replaces existing files, never creates new ones")
    print("=" * 50)
    print(f"Upstream directory: {upstream_dir}")
    print(f"Translation directory: {translation_dir}")
    print()
    
    # Perform the sync operation
    files_copied, files_skipped, deleted_files = sync_lua_files(upstream_dir, translation_dir)
    
    # Display comprehensive summary
    print()
    print("=" * 50)
    print("SYNC SUMMARY")
    print("=" * 50)
    print(f"Files copied: {files_copied}")
    print(f"Files skipped: {files_skipped}")
    print(f"Files deleted from upstream: {len(deleted_files)}")
    
    # Report deleted files with guidance
    if deleted_files:
        print("\n⚠️  DELETED FILES DETECTED ⚠️")
        print("These files exist in your translation folder but were deleted from upstream:")
        print("-" * 50)
        for deleted_file in sorted(deleted_files):
            print(f"  - {deleted_file}")
        print("-" * 50)
        print("Note: These files still exist in your translation folder.")
        print("Review them manually to decide if they should be kept or removed.")
        print("They might be:")
        print("  • Custom translations that should be preserved")
        print("  • Obsolete files that should be deleted")
        print("  • Files that were moved/renamed in upstream")
    
    # Provide next steps guidance
    print("\n" + "=" * 50)
    print("NEXT STEPS")
    print("=" * 50)
    print("1. Review changes with: git diff")
    print("2. Check for any unexpected modifications")
    print("3. If satisfied, commit changes:")
    print("   git add .")
    print("   git commit -m \"Sync Lua files from upstream\"")
    print("4. If issues found, you can revert with: git checkout -- .")
    print("\nSync completed successfully! 🎉")

if __name__ == "__main__":
    main()
