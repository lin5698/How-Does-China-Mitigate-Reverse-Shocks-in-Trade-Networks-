
import pandas as pd
from pathlib import Path

DATA_FILE = Path("/Users/wuyilin/RCEP/data_acquisition/data/34_years_world_export_import_dataset.csv")

def analyze_coverage():
    print(f"Loading {DATA_FILE}...")
    try:
        df = pd.read_csv(DATA_FILE)
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    print(f"Total Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    
    # Check Years
    if 'Year' in df.columns:
        years = sorted(df['Year'].unique())
        print(f"\nYear Range: {min(years)} - {max(years)}")
        print(f"Recent Years: {years[-5:]}")
    
    # Check Countries
    if 'Partner Name' in df.columns:
        countries = df['Partner Name'].unique()
        print(f"\nTotal Unique Countries: {len(countries)}")
        
        # Check specific key countries
        key_countries = ['China', 'India', 'Japan', 'Australia', 'Indonesia', 'Saudi Arabia', 'Russia']
        print("\nKey Country Coverage:")
        for country in key_countries:
            exists = country in countries
            if exists:
                country_years = df[df['Partner Name'] == country]['Year'].unique()
                print(f"  {country}: Yes ({min(country_years)}-{max(country_years)})")
            else:
                print(f"  {country}: No")

if __name__ == "__main__":
    analyze_coverage()
