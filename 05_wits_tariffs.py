"""
WITS Tariff Data Acquisition
Fetches UNCTAD TRAINS tariff data for RCEP countries

Website: https://wits.worldbank.org/
Note: Most tariff data requires manual download
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, START_YEAR, END_YEAR, DATA_DIR
from utils import save_dataframe, logger, print_data_summary


def download_wits_tariff_instructions():
    """
    Provide detailed instructions for downloading WITS tariff data
    """
    logger.info("\n" + "="*60)
    logger.info("WITS TARIFF DATA DOWNLOAD INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\nWITS tariff data must be downloaded manually:")
    logger.info("\n1. Go to: https://wits.worldbank.org/")
    logger.info("2. Click 'Tariff' > 'Tariff Analysis'")
    logger.info("3. Select parameters:")
    logger.info("   - Reporter: Select RCEP countries one by one")
    logger.info("   - Partner: Select 'All Countries' or specific RCEP partners")
    logger.info(f"   - Year: {START_YEAR} to {END_YEAR}")
    logger.info("   - Product: All products (or specific HS codes)")
    logger.info("   - Tariff Type: MFN Applied, Preferential, or Both")
    logger.info("4. Click 'Retrieve Data'")
    logger.info("5. Export as CSV or Excel")
    logger.info(f"6. Save to: {DATA_DIR}/wits_tariff_[country]_[year].csv")
    
    logger.info("\nKey tariff indicators to download:")
    logger.info("- Simple Average MFN Applied Tariff")
    logger.info("- Weighted Average Applied Tariff")
    logger.info("- Preferential Tariff Rates (RCEP)")
    logger.info("- Tariff Rate Quotas")
    
    logger.info("\nRCEP Countries to download:")
    for code, name in RCEP_COUNTRIES.items():
        logger.info(f"  {code}: {name}")
    
    logger.info("\nAlternative: Use UNCTAD TRAINS directly")
    logger.info("https://trainsonline.unctad.org/")
    
    logger.info("\n" + "="*60)


def process_wits_tariff_files() -> pd.DataFrame:
    """
    Process all manually downloaded WITS tariff files
    
    Returns:
        Combined DataFrame with all tariff data
    """
    tariff_files = list(DATA_DIR.glob("wits_tariff*.csv")) + \
                   list(DATA_DIR.glob("wits_tariff*.xlsx"))
    
    if not tariff_files:
        logger.warning("No WITS tariff files found")
        return pd.DataFrame()
    
    logger.info(f"Found {len(tariff_files)} tariff file(s)")
    
    all_data = []
    for filepath in tariff_files:
        try:
            if filepath.suffix == '.csv':
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            logger.info(f"Loaded {filepath.name}: {len(df)} rows")
            all_data.append(df)
            
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        print_data_summary(combined, "WITS Tariff Data")
        return combined
    
    return pd.DataFrame()


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("WITS Tariff Data Acquisition")
    logger.info("="*60)
    
    # Check for existing files
    df = process_wits_tariff_files()
    
    if not df.empty:
        # Save combined data
        output_file = DATA_DIR / f"wits_tariff_combined_{datetime.now().strftime('%Y%m%d')}.csv"
        save_dataframe(df, output_file)
        logger.info(f"\nCombined tariff data saved to {output_file}")
    else:
        # Provide download instructions
        download_wits_tariff_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("WITS tariff acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
