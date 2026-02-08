"""
Validate User Provided Data
Cross-checks the user's 'rcep_comprehensive_data.csv' against our fetched WDI macro data.
Focuses on GDP consistency to verify data accuracy/authenticity.
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# Add parent directory
sys.path.append(str(Path(__file__).parent.parent))
from config import RCEP_COUNTRIES, DATA_DIR, START_YEAR, END_YEAR

def load_user_data():
    file_path = DATA_DIR / "data" / "rcep_comprehensive_data.csv"
    if not file_path.exists():
        print(f"User data file not found: {file_path}")
        return None
    
    # Check encoding, sometimes these are specific
    try:
        df = pd.read_csv(file_path)
    except UnicodeDecodeError:
        df = pd.read_csv(file_path, encoding='latin1')
        
    print(f"Loaded User Data: {len(df)} rows")
    return df

def load_my_macro_data():
    # Find the macro wdi file
    files = list(DATA_DIR.glob("macro_wdi_*.csv"))
    if not files:
        print("No WDI macro data found.")
        return None
    
    file_path = files[0] # Use the first one found
    df = pd.read_csv(file_path)
    print(f"Loaded WDI Macro Data: {len(df)} rows")
    return df

def validate_gdp(user_df, my_df):
    """
    Compare GDP figures.
    User Data: 'reporter_gdp_billion' (Billion USD)
    My Data: 'GDP (current US$)' (units vary, usually raw USD) inside 'value' column where indicator_name is GDP
    """
    print("\n--- Cross-Checking GDP Data ---")
    
    # Filter my data for GDP
    # In config.py: 'GDP_CURRENT': 'NY.GDP.MKTP.CD'
    # In my script: mapped to 'GDP_CURRENT' key likely? 
    # Let's check the content of macro_wdi csv structure from inspection earlier
    # Columns: country_code, Country, year, indicator_name, series, value
    # indicator_name should be 'GDP_CURRENT' (based on config mapping)
    
    my_gdp = my_df[my_df['indicator_name'] == 'GDP_CURRENT'].copy()
    
    if my_gdp.empty:
        print("No GDP_CURRENT found in WDI data.")
        return

    # Prepare User Data for merge
    # User data key: 'reporter' (Country Name) and 'year'
    # Problem: User data uses Country Names (e.g. 'China'), My data uses Codes ('CHN') and Names.
    # We should map User Data names to codes if possible, or use codes if available.
    # User file columns: 'reporter', 'partner', 'year', 'reporter_gdp_billion'...
    # It doesn't seem to have reporter ISO code easily visible in the preview (except 'gdp_reporter' vs 'reporter_gdp_billion').
    # Let's verify if there is a 'reporter_code' or we map names.
    # The preview showed 'China', 'Japan', 'Korea'.
    # Config RCEP_COUNTRIES: 'CHN': 'China'. 'KOR': 'South Korea'. 
    # Note: User data has 'Korea', Config has 'South Korea'. Mapping needed.
    
    country_map = {
        'China': 'CHN', 'CHN': 'CHN',
        'Japan': 'JPN', 'JPN': 'JPN',
        'Korea': 'KOR', 'KOR': 'KOR',
        'Australia': 'AUS', 'AUS': 'AUS',
        'New Zealand': 'NZL', 'NZL': 'NZL',
        'Singapore': 'SGP', 'SGP': 'SGP',
        'Thailand': 'THA', 'THA': 'THA',
        'Vietnam': 'VNM', 'VNM': 'VNM',
        'Indonesia': 'IDN', 'IDN': 'IDN',
        'Malaysia': 'MYS', 'MYS': 'MYS',
        'Philippines': 'PHL', 'PHL': 'PHL',
        'Cambodia': 'KHM', 'KHM': 'KHM',
        'Lao PDR': 'LAO', 'Laos': 'LAO', 'LAO': 'LAO',
        'Myanmar': 'MMR', 'Burma': 'MMR', 'MMR': 'MMR',
        'Brunei Darussalam': 'BRN', 'Brunei': 'BRN', 'BRN': 'BRN'
    }
    
    # Get unique GDP entries from user data (Reporter-Year)
    user_unique = user_df[['reporter', 'year', 'reporter_gdp_billion']].drop_duplicates()
    user_unique['country_code'] = user_unique['reporter'].map(country_map)
    
    # Merge
    merged = pd.merge(user_unique, my_gdp, on=['country_code', 'year'], how='inner', suffixes=('_user', '_wdi'))
    
    # Compare
    # User: Billion USD
    # WDI: Raw USD
    merged['wdi_gdp_billion'] = merged['value'] / 1e9
    merged['diff_percent'] = abs(merged['reporter_gdp_billion'] - merged['wdi_gdp_billion']) / merged['wdi_gdp_billion'] * 100
    
    print(f"Matched {len(merged)} Country-Year points for GDP comparison.")
    
    # Report discrepancies > 5%
    discrepancies = merged[merged['diff_percent'] > 5]
    
    if discrepancies.empty:
        print("✅ SUCCESS: All GDP figures match within 5% tolerance.")
    else:
        print(f"⚠️ WARNING: Found {len(discrepancies)} discrepancies (>5%):")
        print(discrepancies[['reporter', 'year', 'reporter_gdp_billion', 'wdi_gdp_billion', 'diff_percent']].head(10))
        
    # Calculate Correlation
    corr = merged['reporter_gdp_billion'].corr(merged['wdi_gdp_billion'])
    print(f"Correlation between User Data and World Bank Data: {corr:.4f}")

def validate_coverage(user_df):
    print("\n--- Checking Data Coverage ---")
    years = sorted(user_df['year'].unique())
    print(f"User Data Years: {min(years)} - {max(years)}")
    
    reporters = sorted(user_df['reporter'].unique())
    print(f"Reporters found: {reporters}")
    
    missing_rcep = []
    # Simplified check against known names
    known_names = ['China', 'Japan', 'Korea', 'Australia', 'New Zealand', 'Singapore', 'Thailand', 'Vietnam', 'Indonesia', 'Malaysia', 'Philippines', 'Cambodia', 'Laos', 'Myanmar', 'Brunei']
    # Note: fuzzy matching would be better but simple set check fits for now
    
    print("Record counts per country (top 5):")
    print(user_df['reporter'].value_counts().head(5))

def main():
    user_df = load_user_data()
    my_df = load_my_macro_data()
    
    if user_df is not None and my_df is not None:
        validate_coverage(user_df)
        validate_gdp(user_df, my_df)

if __name__ == "__main__":
    main()
