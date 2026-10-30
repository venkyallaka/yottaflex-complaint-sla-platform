"""
CLI Entry point to run the synthetic data generator.
Fulfills Steps 2, 3, 4, 5, 6, 7, 9 of the Granular Instructions.
"""
import argparse
import sys
import os

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.generator.generator import DatasetGenerator

def main():
    parser = argparse.ArgumentParser(description="Synthetic Data Generator for YottaFlex Complaint & SLA System")
    parser.add_argument("--seed", type=int, default=20261022, help="Deterministic PRNG seed (default: 20261022)")
    parser.add_argument("--scale", type=float, default=1.0, help="Scale factor (1.0 = 5k customers, 8k orders, 2k complaints, 6k messages)")
    parser.add_argument("--output", type=str, default="data", help="Output directory for generated artifacts")
    
    args = parser.parse_args()
    print("=================================================================")
    print("      YottaFlex AI - Synthetic Data Generation Pipeline         ")
    print("=================================================================")
    print(f"[*] Configuration: Seed={args.seed} | Scale={args.scale} | Output={args.output}")
    
    generator = DatasetGenerator(seed=args.seed, scale=args.scale)
    generator.generate_all()
    generator.export_data(output_dir=args.output)
    print("=================================================================")
    print("[SUCCESS] Dataset generation completed successfully.")

if __name__ == "__main__":
    main()

