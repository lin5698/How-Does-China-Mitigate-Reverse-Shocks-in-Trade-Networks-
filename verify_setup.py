"""
Verification Script for RCEP Data Acquisition Setup
Checks environment, dependencies, and directory structure
"""

import sys
import os
from pathlib import Path
import importlib

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from config import DATA_DIR, RCEP_COUNTRIES

def check_dependencies():
    print("Checking dependencies...")
    required = [
        'pandas', 'numpy', 'requests', 'networkx', 
        'openpyxl', 'wbgapi'
    ]
    
    missing = []
    for package in required:
        try:
            importlib.import_module(package)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [MISSING] {package}")
            missing.append(package)
            
    if missing:
        print(f"\nWARNING: Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
    else:
        print("\nAll dependencies installed.")

def check_directories():
    print("\nChecking directory structure...")
    
    dirs = [
        DATA_DIR,
        DATA_DIR / "wiod",
        DATA_DIR / "adb_mrio",
        DATA_DIR / "cepii_gravity"
    ]
    
    for d in dirs:
        if not d.exists():
            print(f"  [CREATE] {d}")
            d.mkdir(parents=True, exist_ok=True)
        else:
            print(f"  [OK] {d}")

def check_config():
    print("\nChecking configuration...")
    print(f"  RCEP Members: {len(RCEP_COUNTRIES)}")
    print(f"  Data Directory: {DATA_DIR}")
    
    # Check .env
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        print("  [OK] .env file found")
    else:
        print("  [WARNING] .env file not found (copy .env.example)")

def main():
    print("="*60)
    print("RCEP Data Acquisition Verification")
    print("="*60)
    
    check_dependencies()
    check_directories()
    check_config()
    
    print("\n" + "="*60)
    print("Setup complete! You can now run the acquisition scripts.")
    print("See README.md for execution order.")
    print("="*60)

if __name__ == "__main__":
    main()
