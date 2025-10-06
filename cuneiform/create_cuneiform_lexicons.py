#!/usr/bin/env python3
"""
Create All Cuneiform Lexicon Packages

This unified script builds both Sumerian and Akkadian lexicon packages.

Usage:
    python3 create_cuneiform_lexicons.py              # Build both lexicons
    python3 create_cuneiform_lexicons.py --download   # Download fresh data first
    python3 create_cuneiform_lexicons.py sumerian     # Build only Sumerian
    python3 create_cuneiform_lexicons.py akkadian     # Build only Akkadian
"""

import argparse
import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent

# Build scripts
SUMERIAN_SCRIPT = SCRIPT_DIR / 'create_sumerian_lexicon.py'
AKKADIAN_SCRIPT = SCRIPT_DIR / 'create_akkadian_lexicon.py'

# Output files
SUMERIAN_ZIP = SCRIPT_DIR / 'sumerian_lexicon.zip'
AKKADIAN_ZIP = SCRIPT_DIR / 'akkadian_lexicon.zip'

def run_script(script_path, download=False):
    """Run a build script"""
    cmd = [sys.executable, str(script_path)]
    if download:
        cmd.append('--download')

    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(
        description='Create Cuneiform Lexicon Packages (Sumerian + Akkadian)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 create_cuneiform_lexicons.py              # Build both lexicons
  python3 create_cuneiform_lexicons.py --download   # Download fresh data first
  python3 create_cuneiform_lexicons.py sumerian     # Build only Sumerian
  python3 create_cuneiform_lexicons.py akkadian     # Build only Akkadian

Output:
  - sumerian_lexicon.zip  (ePSD2, 15,940+ entries)
  - akkadian_lexicon.zip  (RINAP, 3,651+ entries)

License: CC BY-SA (Creative Commons Attribution-ShareAlike)
Source: ORACC (Open Richly Annotated Cuneiform Corpus)
        """
    )

    parser.add_argument(
        'language',
        nargs='?',
        choices=['sumerian', 'akkadian', 'both'],
        default='both',
        help='Which lexicon(s) to build (default: both)'
    )

    parser.add_argument(
        '--download',
        action='store_true',
        help='Download fresh data from ORACC before building'
    )

    args = parser.parse_args()

    print("="*60)
    print("Cuneiform Lexicon Package Creator")
    print("="*60)
    print()

    success = True

    # Build Sumerian
    if args.language in ['sumerian', 'both']:
        print("\n" + "="*60)
        print("BUILDING SUMERIAN LEXICON")
        print("="*60)
        print()

        if not run_script(SUMERIAN_SCRIPT, args.download):
            print("\nERROR: Sumerian lexicon build failed")
            success = False
        elif SUMERIAN_ZIP.exists():
            print(f"\n✓ Sumerian lexicon ready: {SUMERIAN_ZIP}")

    # Build Akkadian
    if args.language in ['akkadian', 'both']:
        print("\n" + "="*60)
        print("BUILDING AKKADIAN LEXICON")
        print("="*60)
        print()

        if not run_script(AKKADIAN_SCRIPT, args.download):
            print("\nERROR: Akkadian lexicon build failed")
            success = False
        elif AKKADIAN_ZIP.exists():
            print(f"\n✓ Akkadian lexicon ready: {AKKADIAN_ZIP}")

    # Summary
    print("\n" + "="*60)
    if success:
        print("✓ ALL LEXICONS BUILT SUCCESSFULLY")
    else:
        print("✗ SOME LEXICONS FAILED")
    print("="*60)
    print()

    if success and args.language == 'both':
        print("Output packages:")
        if SUMERIAN_ZIP.exists():
            print(f"  - {SUMERIAN_ZIP}")
        if AKKADIAN_ZIP.exists():
            print(f"  - {AKKADIAN_ZIP}")
        print()
        print("Next steps:")
        print("  1. Copy lexicon ZIPs to app assets")
        print("  2. Import lexicons in app settings")
        print("  3. Test dictionary lookups in cuneiform texts")
        print()

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
