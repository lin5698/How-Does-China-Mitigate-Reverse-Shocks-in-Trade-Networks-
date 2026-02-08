"""
Generate BRI Macro, Trade, and Tariff Report (2013-2023)
Focuses on 5 sample countries: China, India, Russia, Saudi Arabia, Egypt.
Fetches data from World Bank WDI and exports to CSV.
"""

import pandas as pd
import wbgapi as wb
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))
from config import DATA_DIR
from utils import logger

# Configuration for this specific report
REPORT_COUNTRIES = ['CHN', 'IND', 'RUS', 'SAU', 'EGY']
START_YEAR = 2013
END_YEAR = 2023

# Indicator Mapping
INDICATORS = {
    'TM.TAX.MRCH.WM.AR.ZS': 'tariff_weighted_mean',
    'NE.EXP.GNFS.CD': 'exports_goods_services',
    'NE.IMP.GNFS.CD': 'imports_goods_services',
    'NY.GDP.MKTP.CD': 'gdp_current_usd',
    'PX.REX.REER': 'reer',
    'FP.CPI.TOTL.ZG': 'inflation_cpi'
}

def generate_report():
    logger.info("="*60)
    logger.info("Generating BRI Macro & Tariff Report (2013-2023)")
    logger.info(f"Countries: {REPORT_COUNTRIES}")
    logger.info("="*60)

    try:
        # Fetch data
        # wbgapi expects years as integers
        # It's more efficient to fetch all indicators for these countries at once
        
        logger.info("Fetching data from World Bank WDI...")
        
        df = wb.data.DataFrame(
            series=INDICATORS.keys(), 
            economy=REPORT_COUNTRIES, 
            time=range(START_YEAR, END_YEAR + 1), 
            numericTimeKeys=True,
            labels=True
        ).reset_index()
        
        # The dataframe format from wbgapi with labels=True usually is:
        # economy, Series, time dim... (wide) OR mostly usually multi-index if not careful.
        # Let's inspect standard output: usually it has 'economy' index if not reset.
        # With numericTimeKeys=True, columns are years 2013, 2014...
        # Wait, fetching multiple series returns a MultiIndex (economy, series) usually?
        # Let's use `data.DataFrame` which pivots years to columns. 
        # But we want a tidy format or specific format? 
        # The user requested columns: [tariff..., exports..., gdp...]
        # So we likely want rows = Country-Year, Columns = Indicators.
        
        # Let's use `fetch` generator for better control to reshape
        data = []
        for row in wb.data.fetch(INDICATORS.keys(), economy=REPORT_COUNTRIES, time=range(START_YEAR, END_YEAR + 1)):
            data.append({
                'country_code': row['economy'],
                'year': int(row['time'].replace('YR', '')) if isinstance(row['time'], str) else row['time'],
                'indicator': row['series'],
                'value': row['value']
            })
            
        df_long = pd.DataFrame(data)
        
        # Map indicator codes to names
        df_long['indicator_name'] = df_long['indicator'].map(INDICATORS)
        
        # Pivot to wide format: Index=(country_code, year), Columns=indicator_name
        df_wide = df_long.pivot_table(index=['country_code', 'year'], columns='indicator_name', values='value').reset_index()
        
        # Add Country Name (Helper)
        country_names = wb.economy.DataFrame(REPORT_COUNTRIES)['name'].to_dict()
        df_wide.insert(1, 'Country', df_wide['country_code'].map(country_names))
        
        # Sort
        df_wide = df_wide.sort_values(['country_code', 'year'])
        
        # Save
        filename = f"bri_macro_trade_tariff_{START_YEAR}_{END_YEAR}.csv"
        filepath = DATA_DIR / filename
        
        # Round values for cleaner output (optional, but 2 decimals for % and Millions for others is good, but let's keep raw for CSV)
        # Maybe round percentages to 2 decimals
        cols_pct = ['tariff_weighted_mean', 'inflation_cpi']
        for col in cols_pct:
            if col in df_wide.columns:
                df_wide[col] = df_wide[col].round(2)
                
        df_wide.to_csv(filepath, index=False)
        logger.info(f"✅ Report saved to: {filepath}")
        logger.info(f"Total Rows: {len(df_wide)}")
        print(df_wide.head())
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_report()
