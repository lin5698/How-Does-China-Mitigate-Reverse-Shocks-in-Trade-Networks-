"""
World Bank WDI Tariff Indicators
Fetches tariff statistics from World Development Indicators

API: wbgapi (World Bank API)
Documentation: https://pypi.org/project/wbgapi/
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, RCEP_ISO2, START_YEAR, END_YEAR, DATA_DIR
from utils import save_dataframe, logger, print_data_summary, load_wdi_from_csv

try:
    import wbgapi as wb
    WB_AVAILABLE = True
except ImportError:
    WB_AVAILABLE = False
    logger.warning("wbgapi not installed. Run: pip install wbgapi")


# World Bank tariff indicators
TARIFF_INDICATORS = {
    'TM.TAX.MRCH.SM.AR.ZS': 'Tariff rate, applied, simple mean, all products (%)',
    'TM.TAX.MRCH.WM.AR.ZS': 'Tariff rate, applied, weighted mean, all products (%)',
    'TM.TAX.MANF.SM.AR.ZS': 'Tariff rate, applied, simple mean, manufactured products (%)',
    'TM.TAX.MANF.WM.AR.ZS': 'Tariff rate, applied, weighted mean, manufactured products (%)',
    'TM.TAX.TCOM.SM.AR.ZS': 'Tariff rate, most favored nation, simple mean, all products (%)',
    'TM.TAX.TCOM.WM.AR.ZS': 'Tariff rate, most favored nation, weighted mean, all products (%)',
}


def fetch_wb_tariff_data(indicator: str, countries: list) -> pd.DataFrame:
    """
    Fetch tariff data from World Bank API
    
    Args:
        indicator: WDI indicator code
        countries: List of ISO2 country codes
    
    Returns:
        DataFrame with tariff data
    """
    if not WB_AVAILABLE:
        logger.error("wbgapi not available")
        return pd.DataFrame()
    
    try:
        logger.info(f"Fetching {indicator}...")
        
        # Fetch data using wbgapi
        data = wb.data.DataFrame(
            indicator,
            countries,
            time=range(START_YEAR, END_YEAR + 1),
            skipBlanks=True,
            labels=True
        )
        
        # Convert to long format
        df = data.reset_index()
        df = df.melt(id_vars=['economy'], var_name='year', value_name='value')
        df['indicator'] = indicator
        df['indicator_name'] = TARIFF_INDICATORS.get(indicator, indicator)
        
        logger.info(f"Fetched {len(df)} observations")
        return df
        
    except Exception as e:
        logger.error(f"Error fetching {indicator}: {e}")
        return pd.DataFrame()


def fetch_all_tariff_indicators() -> pd.DataFrame:
    """
    Fetch all tariff indicators for RCEP countries
    
    Returns:
        Combined DataFrame with all indicators
    """
    # 1. Try local CSV first
    wdi_csv = DATA_DIR / "WDIData.csv"
    if wdi_csv.exists():
        logger.info("Found local WDIData.csv, using it for tariffs...")
        
        target_countries = list(RCEP_COUNTRIES.keys())
        
        df_csv = load_wdi_from_csv(
            wdi_csv, 
            TARIFF_INDICATORS,
            countries=target_countries,
            start_year=START_YEAR,
            end_year=END_YEAR
        )
        
        if df_csv is not None and not df_csv.empty:
            print_data_summary(df_csv, "World Bank Tariff Indicators (CSV)")
            return df_csv

    # 2. API Fallback
    if not WB_AVAILABLE:
        logger.error("Cannot fetch data without wbgapi")
        return pd.DataFrame()
    
    # Use ISO2 codes for World Bank API
    countries = list(RCEP_ISO2.keys())
    
    all_data = []
    for indicator in TARIFF_INDICATORS.keys():
        df = fetch_wb_tariff_data(indicator, countries)
        if not df.empty:
            all_data.append(df)
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print_data_summary(combined, "World Bank Tariff Indicators")
        return combined
    
    return pd.DataFrame()


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("World Bank WDI Tariff Data Acquisition")
    logger.info("="*60)
    
    if not WB_AVAILABLE:
        logger.error("\nwbgapi package not installed!")
        logger.info("Install with: pip install wbgapi")
        logger.info("\nAlternative: Download manually from:")
        logger.info("https://databank.worldbank.org/")
        logger.info("Select 'World Development Indicators'")
        logger.info("Choose tariff indicators and RCEP countries")
        return
    
    # Fetch data
    df = fetch_all_tariff_indicators()
    
    if not df.empty:
        # Save data
        output_file = DATA_DIR / f"worldbank_tariffs_{datetime.now().strftime('%Y%m%d')}.csv"
        save_dataframe(df, output_file)
        
        # Create pivot table for easier analysis
        pivot = df.pivot_table(
            index=['economy', 'year'],
            columns='indicator_name',
            values='value'
        ).reset_index()
        
        pivot_file = DATA_DIR / f"worldbank_tariffs_pivot_{datetime.now().strftime('%Y%m%d')}.csv"
        save_dataframe(pivot, pivot_file)
        
        logger.info(f"\nSaved data to:")
        logger.info(f"  {output_file}")
        logger.info(f"  {pivot_file}")
    
    logger.info("\n" + "="*60)
    logger.info("World Bank tariff acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
