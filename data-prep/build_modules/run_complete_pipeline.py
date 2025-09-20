#!/usr/bin/env python3
"""
Run the complete dictionary and morphology extraction pipeline.
This script coordinates all the extraction steps with proper error handling.
"""

import subprocess
import sys
from pathlib import Path
import time

def run_command(cmd, description, cwd=None, timeout=None):
    """Run a command with proper error handling"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    try:
        start_time = time.time()
        result = subprocess.run(
            cmd, 
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode != 0:
            print(f"ERROR: Command failed with return code {result.returncode}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            raise RuntimeError(f"{description} failed")
            
        print(f"✓ Completed successfully in {elapsed:.1f} seconds")
        return result
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Command timed out after {timeout} seconds")
        raise RuntimeError(f"{description} timed out")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        raise

def main():
    """Run the complete pipeline"""

    build_modules_dir = Path(__file__).parent
    data_prep_dir = build_modules_dir.parent
    wiktionary_dir = data_prep_dir / "wiktionary-processing"
    
    print("COMPLETE DICTIONARY AND MORPHOLOGY PIPELINE")
    print("="*60)
    
    # Step 1: Ensure Greek pages are extracted (one-time only)
    greek_pages_file = wiktionary_dir / "all_greek_wiktionary_pages.json"
    if not greek_pages_file.exists():
        run_command(
            [sys.executable, "extract_all_greek_pages.py"],
            "Extracting Greek pages from Wiktionary (one-time, ~10 minutes)",
            cwd=wiktionary_dir,
            timeout=1200  # 20 minutes
        )
    else:
        print(f"\n✓ Greek pages already extracted: {greek_pages_file}")
    
    # Step 2: Extract all morphology data
    print("\n\nSTEP 2: EXTRACTING MORPHOLOGY DATA")
    
    morphology_scripts = [
        ("extract_ancient_greek_conjugations.py", "Ancient Greek verb conjugations", 300),
        ("extract_ancient_greek_declensions.py", "Ancient Greek noun declensions", 300),
        ("extract_all_ancient_greek_words_with_diacritics.py", "All Ancient Greek words with diacritics", 300),
        ("extract_inflection_of_template_fixed.py", "Inflection_of template mappings", 300),
        ("extract_declension_mappings_fixed.py", "Declension template mappings", 300)
    ]
    
    for script, desc, timeout in morphology_scripts:
        run_command(
            [sys.executable, script],
            f"Extracting {desc}",
            cwd=wiktionary_dir,
            timeout=timeout
        )
    
    # Step 3: Combine morphology
    run_command(
        [sys.executable, "combine_all_ancient_greek_morphology.py"],
        "Combining all Ancient Greek morphology",
        cwd=wiktionary_dir,
        timeout=300
    )
    
    # Step 4: Extract dictionary data
    print("\n\nSTEP 3: EXTRACTING DICTIONARY DATA")
    
    dictionary_scripts = [
        ("extract_cunliffe_new.py", "Cunliffe dictionary", 300),
        ("extract_lsj_fixed.py", "LSJ dictionary", 300),
        ("extract_wiktionary_final.py", "Wiktionary dictionary entries", 600)
    ]
    
    for script, desc, timeout in dictionary_scripts:
        run_command(
            [sys.executable, script],
            f"Extracting {desc}",
            cwd=build_modules_dir,
            timeout=timeout
        )
    
    # Step 5: Combine dictionaries and create lemma mappings
    print("\n\nSTEP 4: COMBINING DICTIONARIES")
    
    # First create the base combined files - use fixed version
    combine_script = build_modules_dir / "quick_combine_minimal_fixed.py"
    if combine_script.exists():
        run_command(
            [sys.executable, "quick_combine_minimal_fixed.py"],
            "Creating combined dictionary and base lemma mappings (with multi-source support)",
            cwd=build_modules_dir,
            timeout=300
        )
    else:
        # Fallback to original if fixed doesn't exist
        combine_script = build_modules_dir / "quick_combine_minimal.py"
        if combine_script.exists():
            run_command(
                [sys.executable, "quick_combine_minimal.py"],
                "Creating combined dictionary and base lemma mappings",
                cwd=build_modules_dir,
                timeout=300
            )
        else:
            print("ERROR: No combine script found")
            raise FileNotFoundError("Missing combine script")
    
    # Step 6: Generate variants
    print("\n\nSTEP 5: GENERATING VARIANTS")
    
    variant_scripts = [
        ("normalize_unicode.py", "Normalizing Unicode", 60),
        ("add_grave_accent_variants.py", "Adding grave accent variants", 300),
        ("add_enclitic_variants.py", "Adding enclitic variants", 60)
    ]
    
    for script, desc, timeout in variant_scripts:
        run_command(
            [sys.executable, script],
            f"{desc}",
            cwd=build_modules_dir,
            timeout=timeout
        )
    
    # Final check
    print("\n\nFINAL VERIFICATION")
    print("="*60)
    
    required_files = [
        (build_modules_dir / "combine_dictionaries_to_lemma_map_1.json", "Combined dictionary entries"),
        (build_modules_dir / "add_enclitic_variants.json", "Final lemma mappings with variants"),
        (wiktionary_dir / "combine_all_ancient_greek_morphology.json", "Complete morphology data")
    ]
    
    all_good = True
    for file_path, desc in required_files:
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"✓ {desc}: {size_mb:.1f} MB")
        else:
            print(f"✗ MISSING: {desc}")
            all_good = False
    
    if all_good:
        print("\n✓ ALL FILES GENERATED SUCCESSFULLY!")
        print("\nThe pipeline is complete. You can now run create_perseus_database.py")
    else:
        print("\n✗ SOME FILES ARE MISSING - PIPELINE FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()