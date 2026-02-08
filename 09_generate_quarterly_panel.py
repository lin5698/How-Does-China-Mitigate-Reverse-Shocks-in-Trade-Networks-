
import pandas as pd
import numpy as np
from pathlib import Path
import logging

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
DATA_DIR = Path("data_acquisition/data")

def expand_macro_quarterly(df_annual):
    """
    Expands Annual Macro Data to Quarterly.
    Uses 'Quadratic' interpolation for smooth evolution of stock/flow variables.
    Preserves the sum/mean logic depending on variable type (conceptual).
    Here we use a simplified cubic spline for smoothness which is standard for VAR inputs when raw Q data is missing.
    """
    logger.info("Disaggregating Macro Panel (Annual -> Quarterly)...")
    
    quarterly_dfs = []
    
    for iso in df_annual['iso3'].unique():
        sub = df_annual[df_annual['iso3'] == iso].sort_values('year')
        if sub.empty: continue
        
        # Create Annual Date Index (End of Year)
        sub['date'] = pd.to_datetime(sub['year'].astype(str) + '-12-31')
        sub = sub.set_index('date')
        
        # Resample to Quarterly End
        # upscale
        sub_q = sub.resample('QE').asfreq()
        
        # Interpolate
        # Variables like GDP, Population, Tariff are smooth.
        # Use cubic spline for high quality smoothness
        cols_to_interp = [c for c in sub.columns if c not in ['iso3', 'year', 'date']]
        
        sub_q[cols_to_interp] = sub_q[cols_to_interp].interpolate(method='cubic')
        
        # Fill 'iso3'
        sub_q['iso3'] = iso
        
        # Create 'year' and 'quarter' columns
        sub_q['year'] = sub_q.index.year
        sub_q['quarter'] = sub_q.index.quarter
        
        # Keep only 2005-2024 range fully
        sub_q = sub_q[(sub_q.index.year >= 2005) & (sub_q.index.year <= 2024)]
        
        quarterly_dfs.append(sub_q)
        
    df_q = pd.concat(quarterly_dfs)
    return df_q.reset_index().rename(columns={'date': 'date_quarterly'})

def expand_bilateral_quarterly(df_annual):
    """
    Expands Bilateral Trade Data to Quarterly.
    """
    logger.info("Disaggregating Bilateral Trade Panel (Annual -> Quarterly)...")
    
    quarterly_dfs = []
    
    # Process unique reporter-partner pairs
    pairs = df_annual[['reporter_iso', 'partner_iso']].drop_duplicates()
    
    logger.info(f"Processing {len(pairs)} country pairs...")
    
    for _, pair in pairs.iterrows():
        rep, par = pair['reporter_iso'], pair['partner_iso']
        sub = df_annual[(df_annual['reporter_iso'] == rep) & (df_annual['partner_iso'] == par)].sort_values('year')
        
        if len(sub) < 2: continue # Need at least 2 points to interp
        
        # Deduplicate to ensure unique index
        # If duplicates exist for same year, take the mean (safe assumption for mixed sources)
        sub = sub.groupby('year', as_index=False).mean(numeric_only=True)
        
        sub['date'] = pd.to_datetime(sub['year'].astype(str) + '-12-31')
        sub = sub.set_index('date')
        
        # Resample
        sub_q = sub.resample('QE').asfreq()
        
        # Interpolate numeric columns
        cols_to_interp = ['export_usd', 'import_usd', 'bilateral_tariff'] # Add others if needed
        # Check existence
        cols_present = [c for c in cols_to_interp if c in sub.columns]
        
        # For flows (exports), we want the annual sum to roughly match. 
        # Simple cubic interpolation on the *levels* preserves the trend.
        # Ideally, we divide annual by 4 and then smooth, but direct interp of levels implies 
        # the 'rate' at Q4 matches Annual. 
        # Better: Divide Annual by 4 first, set to mid-year, then interp?
        # Simplified approach: Cubic Interpolation of values.
        
        sub_q[cols_present] = sub_q[cols_present].interpolate(method='pchip') # PCHIP preserves monotonic trends better
        
        # Divide flow variables by 4 to estimate quarterly flow? 
        # Or treat the input as "Annual Rate"?
        # Usually VAR uses Log Levels.
        # Let's divide by 4 to simulate actual quarterly magnitude.
        for c in ['export_usd', 'import_usd']:
            if c in sub_q.columns:
                sub_q[c] = sub_q[c] / 4.0
                
        # Fill categorical
        sub_q['reporter_iso'] = rep
        sub_q['partner_iso'] = par
        sub_q['year'] = sub_q.index.year
        sub_q['quarter'] = sub_q.index.quarter
        
        quarterly_dfs.append(sub_q)
        
    df_q = pd.concat(quarterly_dfs)
    return df_q.reset_index().rename(columns={'date': 'date_quarterly'})

def main():
    # Load Master Annual
    macro_path = DATA_DIR / "master_macro_panel_2005_2024.csv"
    bilat_path = DATA_DIR / "master_bilateral_trade_2005_2024.csv"
    
    if not macro_path.exists() or not bilat_path.exists():
        logger.error("Master annual files not found. Run synthesis first.")
        return

    df_macro = pd.read_csv(macro_path)
    df_bilat = pd.read_csv(bilat_path)
    
    # 1. Macro
    df_macro_q = expand_macro_quarterly(df_macro)
    out_macro = DATA_DIR / "master_quarterly_macro_2005_2024.csv"
    df_macro_q.to_csv(out_macro, index=False)
    logger.info(f"Saved Quarterly Macro: {len(df_macro_q)} rows to {out_macro}")
    
    # 2. Bilateral
    df_bilat_q = expand_bilateral_quarterly(df_bilat)
    out_bilat = DATA_DIR / "master_quarterly_bilateral_2005_2024.csv"
    df_bilat_q.to_csv(out_bilat, index=False)
    logger.info(f"Saved Quarterly Bilateral: {len(df_bilat_q)} rows to {out_bilat}")
    
    # Validation Code
    print("\n--- Validation Report ---")
    print(f"Time Horizon: 2005 Q1 - 2024 Q4")
    print(f"Total Quarters: {(2024-2005+1)*4}")
    print(f"Macro Rows: {len(df_macro_q)}")
    print(f"Bilateral Rows: {len(df_bilat_q)}")
    print("Sample Date:", df_macro_q['date_quarterly'].iloc[0])

if __name__ == "__main__":
    main()
