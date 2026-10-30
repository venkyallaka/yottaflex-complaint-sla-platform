"""
Reproducibility Verification Suite.
Fulfills Step 10 of the instructions:
Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.
"""
import os
import sys
import shutil
import tempfile
import hashlib
from typing import Dict

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.generator.generator import DatasetGenerator

def hash_file(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    seed = 20261022
    scale = 0.2  # Fast verification scale for reproducibility check
    
    print("=================================================================")
    print("       YottaFlex AI - Seed Reproducibility Verification Suite    ")
    print("=================================================================")
    print(f"[*] Testing Seed: {seed} | Test Scale: {scale}")
    
    temp_dir_1 = tempfile.mkdtemp(prefix="yotta_run1_")
    temp_dir_2 = tempfile.mkdtemp(prefix="yotta_run2_")
    
    try:
        # Run 1
        print(f"\n[1/3] Generating Run 1 to {temp_dir_1}...")
        gen1 = DatasetGenerator(seed=seed, scale=scale)
        gen1.generate_all()
        manifest1 = gen1.export_data(temp_dir_1)
        
        # Run 2
        print(f"\n[2/3] Generating Run 2 to {temp_dir_2} with identical seed...")
        gen2 = DatasetGenerator(seed=seed, scale=scale)
        gen2.generate_all()
        manifest2 = gen2.export_data(temp_dir_2)
        
        # Compare
        print("\n[3/3] Comparing Row Counts and SHA-256 Checksums across all artifacts...")
        print(f"{'Table / Artifact':<32} | {'Run 1 Count':<11} | {'Run 2 Count':<11} | {'Checksum Match':<14}")
        print("-" * 75)
        
        all_matched = True
        for table, count1 in manifest1["table_counts"].items():
            count2 = manifest2["table_counts"].get(table, 0)
            csv_file1 = os.path.join(temp_dir_1, "csv", f"{table}.csv")
            csv_file2 = os.path.join(temp_dir_2, "csv", f"{table}.csv")
            
            h1 = hash_file(csv_file1)
            h2 = hash_file(csv_file2)
            
            match = (count1 == count2) and (h1 == h2)
            if not match:
                all_matched = False
            status = "IDENTICAL [PASS]" if match else "MISMATCH [FAIL]"
            print(f"{table:<32} | {count1:<11} | {count2:<11} | {status:<14}")
            
        print("=" * 75)
        if all_matched:
            print("[SUCCESS] 100% Deterministic Reproducibility Confirmed! Seed guarantees bit-level fidelity.")
            sys.exit(0)
        else:
            print("[FAILURE] Non-deterministic variation detected between runs.")
            sys.exit(1)
            
    finally:
        shutil.rmtree(temp_dir_1, ignore_errors=True)
        shutil.rmtree(temp_dir_2, ignore_errors=True)

if __name__ == "__main__":
    main()
