"""
Weight Matrix Construction
Constructs trade weight matrices (W) for RCEP and BRI networks.
Calculates row-normalized weights and high-order powers (W^2, W^3) for indirect effects.

Input: Bilateral Trade Data (CSV) - Prioritizes User Supplied 'rcep_comprehensive_data.csv'
Output: Weight Matrices (CSV)
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from config import (RCEP_COUNTRIES, BRI_COUNTRIES, START_YEAR, END_YEAR, DATA_DIR, 
                    NETWORK_WEIGHT_THRESHOLD)
from utils import save_dataframe, load_dataframe, logger, print_data_summary

# Robust Country Map (Name -> ISO3)
COUNTRY_MAP = {
    'China': 'CHN', 'CHN': 'CHN',
    'Japan': 'JPN', 'JPN': 'JPN',
    'Korea': 'KOR', 'South Korea': 'KOR', 'Republic of Korea': 'KOR', 'KOR': 'KOR',
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
    'Brunei Darussalam': 'BRN', 'Brunei': 'BRN', 'BRN': 'BRN',
    # Common BRI Countries
    'Russia': 'RUS', 'RUS': 'RUS',
    'Pakistan': 'PAK', 'PAK': 'PAK',
    'India': 'IND', 'IND': 'IND',
    'Bangladesh': 'BGD', 'BGD': 'BGD',
    'Turkey': 'TUR', 'Turkiye': 'TUR', 'TUR': 'TUR',
    'Iran': 'IRN', 'Islamic Republic of Iran': 'IRN', 'IRN': 'IRN',
    'Saudi Arabia': 'SAU', 'SAU': 'SAU',
    'United Arab Emirates': 'ARE', 'UAE': 'ARE', 'ARE': 'ARE',
    'Egypt': 'EGY', 'EGY': 'EGY',
    'Nigeria': 'NGA', 'NGA': 'NGA',
    'South Africa': 'ZAF', 'ZAF': 'ZAF',
    'Brazil': 'BRA', 'BRA': 'BRA',
    'Kazakhstan': 'KAZ', 'KAZ': 'KAZ'
}

def standardize_data(df):
    """
    Standardize the input dataframe to columns: ['reporter', 'partner', 'year', 'value']
    and ISO3 country codes.
    """
    cols = df.columns
    
    # 1. Identify Columns
    # Reporter
    if 'reporterCode' in cols: rep_col = 'reporterCode'
    elif 'reporter' in cols: rep_col = 'reporter'
    else: return None
    
    # Partner
    if 'partnerCode' in cols: par_col = 'partnerCode'
    elif 'partner' in cols: par_col = 'partner'
    else: return None
    
    # Year
    if 'period' in cols: year_col = 'period'
    elif 'year' in cols: year_col = 'year'
    else: return None
    
    # Value (Prefer Export Value for W matrix)
    if 'export_value' in cols: val_col = 'export_value'
    elif 'primaryValue' in cols: val_col = 'primaryValue'
    elif 'trade_value' in cols: val_col = 'trade_value'
    elif 'value' in cols: val_col = 'value'
    else: return None
    
    logger.info(f"Mapping columns: R={rep_col}, P={par_col}, Y={year_col}, V={val_col}")
    
    # 2. Rename and Select
    df_std = df[[rep_col, par_col, year_col, val_col]].copy()
    df_std.columns = ['reporter', 'partner', 'year', 'value']
    
    # 3. Map Countries to ISO3
    # Apply mapping, keeping original if not found (though mapped ones are safer for filtering)
    df_std['reporter'] = df_std['reporter'].map(COUNTRY_MAP).fillna(df_std['reporter'])
    df_std['partner'] = df_std['partner'].map(COUNTRY_MAP).fillna(df_std['partner'])
    
    # 4. Clean Data
    # Drop rows where reporter or partner is NaN (or invalid)
    df_std.dropna(subset=['reporter', 'partner', 'value'], inplace=True)
    
    # Convert year to int
    df_std['year'] = pd.to_numeric(df_std['year'], errors='coerce').fillna(0).astype(int)
    
    # Convert value to float
    df_std['value'] = pd.to_numeric(df_std['value'], errors='coerce').fillna(0.0)
    
    return df_std

def construct_matrix(df_year, countries):
    """
    Construct N x N weight matrix for a specific year and country set
    """
    country_codes = sorted(list(countries.keys()))
    n = len(country_codes)
    country_to_idx = {code: i for i, code in enumerate(country_codes)}
    
    # Initialize matrix
    W = np.zeros((n, n))
    
    # Fill Matrix
    # We iterate through the dataframe for this year
    # df_year columns are standardized: reporter, partner, year, value
    
    matched_count = 0
    total_rows = len(df_year)
    
    for _, row in df_year.iterrows():
        r = row['reporter']
        p = row['partner']
        v = row['value']
        
        if r in country_to_idx and p in country_to_idx:
            i = country_to_idx[r]
            j = country_to_idx[p]
            # Simple addition in case of duplicate entries (e.g. from multiple sources)
            # though usually we expect unique pairs. 
            # If standard Comtrade, unique. If mixed, maybe duplicates.
            # We overwrite or add? Overwrite is safer for time-series, Add is risky.
            # Let's overwrite, assuming the last one is good, or sum if split categories?
            # Comtrade usually aggregates TOTAL. 
            W[i, j] = v 
            matched_count += 1
            
    # logger.debug(f"Matched {matched_count}/{total_rows} trade flows for known network countries.")

    # Row normalization
    row_sums = W.sum(axis=1)
    
    # Avoid division by zero
    W_norm = np.zeros_like(W)
    for i in range(n):
        if row_sums[i] > 0:
            W_norm[i, :] = W[i, :] / row_sums[i]
            
    return W_norm, country_codes

def calculate_powers(W, order=3):
    """Calculate powers of W: W, W^2, W^3..."""
    powers = {}
    current_W = W
    for i in range(1, order + 1):
        powers[i] = current_W
        if i < order:
            current_W = np.dot(current_W, W) # Matrix multiplication
    return powers

def main():
    logger.info("="*60)
    logger.info("Weight Matrix Construction")
    logger.info("="*60)
    
    # 1. Load Data
    # Priority: User > Master Bilateral > Comtrade API
    user_file = DATA_DIR / "data" / "rcep_comprehensive_data.csv"
    master_file = DATA_DIR / "master_bilateral_trade_2005_2024.csv"
    comtrade_files = sorted(DATA_DIR.glob("comtrade_*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    df = None
    source_name = ""
    
    if user_file.exists():
        logger.info(f"Using User-Provided Data: {user_file.name}")
        df = load_dataframe(user_file)
        source_name = "User"
    elif master_file.exists():
        logger.info(f"Using Master Bilateral Data: {master_file.name}")
        df = load_dataframe(master_file)
        source_name = "Master"
    elif comtrade_files:
        logger.info(f"Using Comtrade API Data: {comtrade_files[0].name}")
        df = load_dataframe(comtrade_files[0])
        source_name = "Comtrade"
    else:
        logger.error("No trade data files found.")
        return
        
    if df is None or df.empty:
        logger.error("Loaded dataframe is empty.")
        return
        
    # 2. Standardize
    df_clean = standardize_data(df)
    if df_clean is None:
        logger.error("Failed to standardize data columns.")
        return
        
    logger.info(f"Standardized Data: {len(df_clean)} records")
        
    # 3. Process Networks
    networks = {
        'RCEP': RCEP_COUNTRIES,
        'BRI': BRI_COUNTRIES
    }
    
    for net_name, countries in networks.items():
        logger.info(f"\nProcessing Network: {net_name}")
        
        # Determine strict year range from Config but limited by Data Availability
        data_years = sorted(df_clean['year'].unique())
        valid_years = [y for y in data_years if START_YEAR <= y <= END_YEAR]
        
        logger.info(f"Available Years in Data: {len(valid_years)} ({min(valid_years)} - {max(valid_years)})")
        
        processed_count = 0
        for year in valid_years:
            df_year = df_clean[df_clean['year'] == year]
            
            W, codes = construct_matrix(df_year, countries)
            
            # Check sanity - if W is empty/zeros (no matching countries)
            if np.all(W == 0):
                logger.warning(f"Year {year}: No valid trade flows found for {net_name}. Skipping matrix gen.")
                continue

            # Calculate powers
            powers = calculate_powers(W, order=3)
            
            # Save
            timestamp = datetime.now().strftime('%Y%m%d')
            for order, mat in powers.items():
                suffix = "" if order == 1 else f"_power{order}"
                filename = f"weight_matrix_{net_name}_{year}{suffix}.csv"
                filepath = DATA_DIR / "matrices" / filename
                filepath.parent.mkdir(exist_ok=True)
                
                df_mat = pd.DataFrame(mat, index=codes, columns=codes)
                save_dataframe(df_mat, filepath)
            
            processed_count += 1
            
        logger.info(f"Finished {net_name}: Generated matrices for {processed_count} years.")

if __name__ == "__main__":
    main()
