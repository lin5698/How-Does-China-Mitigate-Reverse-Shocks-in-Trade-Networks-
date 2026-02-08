
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = Path("data_acquisition/data")
OUTPUT_FILE = DATA_DIR / "final_rcep_bri_comprehensive_2005_2024.csv"
START_YEAR = 2005
END_YEAR = 2024

# Expanded Country Map (ISO3)
COUNTRY_MAP = {
    'China': 'CHN', 'CHN': 'CHN',
    'Japan': 'JPN', 'JPN': 'JPN',
    'Korea, Rep.': 'KOR', 'South Korea': 'KOR', 'Korea': 'KOR', 'KOR': 'KOR',
    'Australia': 'AUS', 'AUS': 'AUS',
    'New Zealand': 'NZL', 'NZL': 'NZL',
    'Indonesia': 'IDN', 'IDN': 'IDN',
    'Malaysia': 'MYS', 'MYS': 'MYS',
    'Philippines': 'PHL', 'PHL': 'PHL',
    'Singapore': 'SGP', 'SGP': 'SGP',
    'Thailand': 'THA', 'THA': 'THA',
    'Vietnam': 'VNM', 'Viet Nam': 'VNM', 'VNM': 'VNM',
    'Brunei Darussalam': 'BRN', 'Brunei': 'BRN', 'BRN': 'BRN',
    'Cambodia': 'KHM', 'KHM': 'KHM',
    'Lao PDR': 'LAO', 'Laos': 'LAO', 'LAO': 'LAO',
    'Myanmar': 'MMR', 'MMR': 'MMR',
    'India': 'IND', 'IND': 'IND',
    'Russian Federation': 'RUS', 'Russia': 'RUS', 'RUS': 'RUS',
    'Saudi Arabia': 'SAU', 'SAU': 'SAU',
    'Egypt, Arab Rep.': 'EGY', 'Egypt': 'EGY', 'EGY': 'EGY',
    'United States': 'USA', 'USA': 'USA',
    'Germany': 'DEU', 'DEU': 'DEU'
}

def get_iso3(name):
    """Robustly map country name/code to ISO3."""
    if not isinstance(name, str):
        return None
    clean_name = name.strip()
    return COUNTRY_MAP.get(clean_name, COUNTRY_MAP.get(clean_name.title(), None))

def load_and_clean_gdp_v202502():
    """
    Loads and reshapes the wide-format GDP/Macro file.
    Indicators: EXCH, GDP-CAP, GDP-PPP, GDP-PPP-CAP, GDP-VAL, GDP-VOL, POP
    """
    fpath = DATA_DIR / "gdp_v202502.csv"
    if not fpath.exists():
        logger.warning(f"{fpath} not found.")
        return pd.DataFrame()
    
    logger.info(f"Loading macro data: {fpath}")
    df = pd.read_csv(fpath)
    
    # Reshape wide to long
    # Columns: country, indicator, v1960...v2029
    id_vars = ['country', 'indicator']
    value_vars = [c for c in df.columns if c.startswith('v') and c[1:].isdigit()]
    
    df_long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name='year_str', value_name='value')
    df_long['year'] = df_long['year_str'].str.replace('v', '').astype(int)
    
    # Filter years
    df_long = df_long[(df_long['year'] >= START_YEAR) & (df_long['year'] <= END_YEAR)]
    
    # Pivot to have indicators as columns
    df_pivot = df_long.pivot_table(index=['country', 'year'], columns='indicator', values='value').reset_index()
    
    # Rename columns to match our schema
    # GDP-VAL is usually Nominal GDP in Local Currency or USD. Assuming USD from context or will verify.
    # Actually, for global comparison, usually need USD. 
    # Let's map generalized names.
    rename_map = {
        'country': 'iso3',
        'GDP-VAL': 'gdp_current_usd', # Assumption, will verify range
        'POP': 'population',
        'EXCH': 'exchange_rate',
        'GDP-PPP': 'gdp_ppp_current_usd'
    }
    df_pivot = df_pivot.rename(columns=rename_map)
    
    logger.info(f"Macro data loaded: {len(df_pivot)} rows")
    return df_pivot

def load_and_clean_34years_trade():
    """
    Loads the 34-year trade dataset.
    Columns: Partner Name, Year, Export, Import, AHS Weighted Average, etc.
    This file seems to be 'Reporter' centric or 'World' centric?
    Inspection showed 'Partner Name'. Assuming it aggregates trade *with* that partner?
    Or is it bilateral? The snippet had 'Russian Federation' rows with 'Export'/'Import'. 
    If 'Partner Name' is the row identifier and there is no 'Reporter', it might be World->Partner trade?
    Let's re-verify the columns in logic. 
    Wait, inspecting step 230 output: columns are ['Partner Name', 'Year', 'Export', 'Import', ...]
    It doesn't show 'Reporter Name'. This usually implies 'World' is the reporter (reporting exports TO Partner).
    So this gives us:
    - Global Exports TO [Partner]
    - Global Imports FROM [Partner]
    - [Partner]'s Tariffs (AHS/MFN) faced or imposed? usually 'AHS Weighted Average (%)' is what the country imposes if it's country-level data.
    
    Let's treat this as Country-level Monadic (Macro) and Tariff data primarily.
    """
    fpath = DATA_DIR / "34_years_world_export_import_dataset.csv"
    if not fpath.exists():
        logger.warning(f"{fpath} not found.")
        return pd.DataFrame()

    logger.info(f"Loading 34-year dataset: {fpath}")
    df = pd.read_csv(fpath)
    
    # Map Country
    df['iso3'] = df['Partner Name'].apply(get_iso3)
    df = df.dropna(subset=['iso3'])
    
    # Filter Years
    df = df[(df['Year'] >= START_YEAR) & (df['Year'] <= END_YEAR)]
    
    # Select and Rename Columns
    # Assuming 'Export (US$ Thousand)' is Partner's Total Exports? Or World's exports to Partner?
    # Usually in these datasets 'Export' = Country's Exports to World.
    rename_cols = {
        'Year': 'year',
        'Export (US$ Thousand)': 'total_exports_usd_k',
        'Import (US$ Thousand)': 'total_imports_usd_k',
        'AHS Weighted Average (%)': 'tariff_ahs_weighted',
        'MFN Weighted Average (%)': 'tariff_mfn_weighted'
    }
    df = df.rename(columns=rename_cols)
    
    cols_to_keep = ['iso3', 'year', 'total_exports_usd_k', 'total_imports_usd_k', 'tariff_ahs_weighted', 'tariff_mfn_weighted']
    df = df[cols_to_keep]
    
    logger.info(f"34-year data filtered: {len(df)} rows")
    return df

def load_user_rcep_data():
    """Load the user's bilateral RCEP data."""
    fpath = DATA_DIR / "data" / "rcep_comprehensive_data.csv" # Check path structure
    if not fpath.exists():
        # Try alternate path
        fpath = DATA_DIR / "rcep_comprehensive_data.csv"
        
    if not fpath.exists():
        logger.warning("User RCEP data not found.")
        return pd.DataFrame()
        
    df = pd.read_csv(fpath)
    # This is bilateral: reporter, partner, year, export_value, etc.
    # Map ISO3
    df['reporter_iso'] = df['reporter'].apply(get_iso3)
    df['partner_iso'] = df['partner'].apply(get_iso3)
    df = df.dropna(subset=['reporter_iso', 'partner_iso'])
    
    # Standardize
    rename = {
        'export_value': 'export_usd',
        'import_value': 'import_usd',
        'avg_tariff_rate': 'bilateral_tariff' # If this exists
    }
    df = df.rename(columns=rename)
    
    return df

def synthesize():
    logger.info("Starting Synthesis...")
    
    # 1. Macro Data (Monadic)
    # Merge gdp_v202502 (primary) and 34_years (secondary for tariffs/trade totals)
    df_macro_gdp = load_and_clean_gdp_v202502()
    df_macro_34y = load_and_clean_34years_trade()
    
    # Merge on iso3, year
    if not df_macro_gdp.empty and not df_macro_34y.empty:
        df_macro = pd.merge(df_macro_gdp, df_macro_34y, on=['iso3', 'year'], how='outer')
    elif not df_macro_gdp.empty:
        df_macro = df_macro_gdp
    else:
        df_macro = df_macro_34y
        
    # Add WDI fallback if needed (simplified for now, assuming gdp_v202502 is superior)
    
    # 2. Bilateral Trade Data
    df_bilateral = load_user_rcep_data()
    
    # 3. Fill Gaps in Macro from Bilateral totals
    if not df_macro.empty and not df_bilateral.empty:
        logger.info("Filling gaps in macro panel using bilateral totals...")
        
        # Calculate totals from bilateral
        bilat_exp = df_bilateral.groupby(['reporter_iso', 'year'])['export_usd'].sum().reset_index()
        bilat_imp = df_bilateral.groupby(['reporter_iso', 'year'])['import_usd'].sum().reset_index()
        
        # Merge back to macro
        # Assuming export_usd in bilateral is in Billions (check!)
        # In 07 script, China-Japan was ~120 in 2010. That's Billions.
        # total_exports_usd_k is in Thousands.
        # So bill * 1e6 = thousands.
        
        # China-Japan 2010 was 121B. Total world exports in 2010 was 1.3T (1.3e9 k).
        # So 121B is a significant portion of 1.3T.
        
        # Let's align units.
        bilat_exp['bilat_total_exp_k'] = bilat_exp['export_usd'] * 1e6
        bilat_imp['bilat_total_imp_k'] = bilat_imp['import_usd'] * 1e6
        
        df_macro = df_macro.merge(bilat_exp[['reporter_iso', 'year', 'bilat_total_exp_k']], 
                                  left_on=['iso3', 'year'], right_on=['reporter_iso', 'year'], 
                                  how='left')
        df_macro = df_macro.merge(bilat_imp[['reporter_iso', 'year', 'bilat_total_imp_k']], 
                                  left_on=['iso3', 'year'], right_on=['reporter_iso', 'year'], 
                                  how='left')
        
        # Fill missing
        df_macro['total_exports_usd_k'] = df_macro['total_exports_usd_k'].fillna(df_macro['bilat_total_exp_k'])
        df_macro['total_imports_usd_k'] = df_macro['total_imports_usd_k'].fillna(df_macro['bilat_total_imp_k'])
        
        df_macro.drop(columns=['reporter_iso_x', 'reporter_iso_y', 'bilat_total_exp_k', 'bilat_total_imp_k'], inplace=True, errors='ignore')

    macro_output = DATA_DIR / "master_macro_panel_2005_2024.csv"
    df_macro.to_csv(macro_output, index=False)
    logger.info(f"Saved Master Macro Panel to {macro_output}")
    
    # OUTPUT 2: Master Bilateral Trade (Rep-Part-Year)
    # Merge Macro info into Bilateral (Reporter characteristics)
    if not df_bilateral.empty and not df_macro.empty:
        # Merge Reporter Macro
        df_bilateral = df_bilateral.merge(
            df_macro.add_prefix('rep_'), 
            left_on=['reporter_iso', 'year'], 
            right_on=['rep_iso3', 'rep_year'], 
            how='left'
        )
        # Merge Partner Macro
        df_bilateral = df_bilateral.merge(
            df_macro.add_prefix('par_'), 
            left_on=['partner_iso', 'year'], 
            right_on=['par_iso3', 'par_year'], 
            how='left'
        )
        
        # Clean up merge columns
        df_bilateral.drop(columns=['rep_iso3', 'rep_year', 'par_iso3', 'par_year'], inplace=True, errors='ignore')
    
    bilateral_output = DATA_DIR / "master_bilateral_trade_2005_2024.csv"
    df_bilateral.to_csv(bilateral_output, index=False)
    logger.info(f"Saved Master Bilateral Panel to {bilateral_output}")

    # Summary
    print("\nSynthesis Complete.")
    print(f"1. Macro Panel: {len(df_macro)} rows (Countries x Years)")
    print(f"2. Bilateral Panel: {len(df_bilateral)} rows (Trade Flows)")
    print(f"   - Years: {df_bilateral['year'].min()} - {df_bilateral['year'].max()}")
    print(f"   - Reporters: {df_bilateral['reporter_iso'].nunique()}")

if __name__ == "__main__":
    synthesize()
