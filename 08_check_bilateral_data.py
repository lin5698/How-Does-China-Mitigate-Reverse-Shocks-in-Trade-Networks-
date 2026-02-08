
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data_acquisition/data")

def check_file(filename):
    fpath = DATA_DIR / filename
    print(f"\n--- Checking {filename} ---")
    if not fpath.exists():
        print("File not found.")
        return

    try:
        df = pd.read_csv(fpath)
        print(f"Rows: {len(df)}")
        print(f"Columns: {list(df.columns)}")
        
        # Check for Bilateral Structure
        # Look for Reporter/Partner columns
        cols = [c.lower() for c in df.columns]
        
        reporter_col = next((c for c in df.columns if 'reporter' in c.lower() or 'origin' in c.lower()), None)
        partner_col = next((c for c in df.columns if 'partner' in c.lower() or 'destination' in c.lower()), None)
        year_col = next((c for c in df.columns if 'year' in c.lower() or 'period' in c.lower()), None)
        value_col = next((c for c in df.columns if 'value' in c.lower() or 'export' in c.lower() or 'import' in c.lower() or 'trade' in c.lower()), None)

        if reporter_col and partner_col:
            print("Structure: Bilateral (Reporter-Partner detected)")
            reporters = df[reporter_col].nunique()
            partners = df[partner_col].nunique()
            print(f"Unique Reporters: {reporters}")
            print(f"Unique Partners: {partners}")
            
            if year_col:
                years = sorted(df[year_col].unique())
                print(f"Time Range: {min(years)} - {max(years)}")
            
            if value_col:
                total_val = df[value_col].sum()
                print(f"Total Traded Value (Sum): {total_val:,.0f}")
                
            # Sample
            print("\nSample Data:")
            print(df[[reporter_col, partner_col, year_col, value_col]].head(3).to_string(index=False))
            
        else:
            print("Structure: Likely Not Bilateral (Missing Reporter/Partner columns)")
            print("Sample Row:")
            print(df.iloc[0])

    except Exception as e:
        print(f"Error reading file: {e}")

def main():
    files_to_check = [
        "comtrade_bilateral_imports_20220101.csv",
        "rcep_comprehensive_data.csv", 
        "master_bilateral_trade_2005_2024.csv",
        "34_years_world_export_import_dataset.csv"
    ]
    
    for f in files_to_check:
        check_file(f)

if __name__ == "__main__":
    main()
