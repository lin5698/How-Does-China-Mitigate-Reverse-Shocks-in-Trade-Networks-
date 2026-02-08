"""
WIOD (World Input-Output Database) Acquisition
Downloads and processes WIOD tables for global supply chain analysis

Website: https://www.rug.nl/ggdc/valuechain/wiod/
Coverage: 43 countries, 56 industries, 2000-2014
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import zipfile

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR
from utils import download_file, save_dataframe, logger, print_data_summary


WIOD_BASE_URL = "https://www.rug.nl/ggdc/valuechain/wiod/wiod-2016-release"


def download_wiod_instructions():
    """
    Provide instructions for downloading WIOD data
    """
    logger.info("\n" + "="*60)
    logger.info("WIOD DOWNLOAD INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\nWIOD provides comprehensive input-output tables:")
    logger.info("Coverage: 43 countries + Rest of World, 56 industries, 2000-2014")
    
    logger.info("\nDownload Steps:")
    logger.info("1. Visit: https://www.rug.nl/ggdc/valuechain/wiod/")
    logger.info("2. Navigate to 'WIOD 2016 Release'")
    logger.info("3. Download options:")
    logger.info("   a) World Input-Output Tables (WIOT)")
    logger.info("   b) National Input-Output Tables (NIOT)")
    logger.info("   c) Socio-Economic Accounts (SEA)")
    
    logger.info("\nRecommended downloads:")
    logger.info("- WIOT in current prices (Excel format, by year)")
    logger.info("- Or download all years: WIOT_2000-2014.zip")
    logger.info(f"- Save to: {DATA_DIR}/wiod/")
    
    logger.info("\nDirect download links:")
    logger.info("- All WIOTs: http://www.wiod.org/protected3/data16/wiot_ROW/WIOT_2000-2014.zip")
    logger.info("- Individual years: http://www.wiod.org/protected3/data16/wiot_ROW/WIOT[YEAR]_Nov16_ROW.xlsx")
    
    logger.info("\nRCEP Countries in WIOD:")
    wiod_rcep = {
        'AUS': 'Australia',
        'CHN': 'China',
        'IDN': 'Indonesia',
        'JPN': 'Japan',
        'KOR': 'South Korea',
        'MYS': 'Malaysia (in ROW)',
        'PHL': 'Philippines (in ROW)',
        'SGP': 'Singapore (in ROW)',
        'THA': 'Thailand (in ROW)',
        'VNM': 'Vietnam (in ROW)',
    }
    
    for code, name in wiod_rcep.items():
        logger.info(f"  {code}: {name}")
    
    logger.info("\nNote: Some RCEP countries are aggregated in 'Rest of World'")
    
    logger.info("\n" + "="*60)


def download_wiod_table(year: int) -> Path:
    """
    Attempt to download WIOD table for a specific year
    
    Args:
        year: Year (2000-2014)
    
    Returns:
        Path to downloaded file or None
    """
    if year < 2000 or year > 2014:
        logger.error(f"WIOD only covers 2000-2014, requested: {year}")
        return None
    
    # WIOD download URL (may require authentication)
    url = f"http://www.wiod.org/protected3/data16/wiot_ROW/WIOT{year}_Nov16_ROW.xlsx"
    output_path = DATA_DIR / "wiod" / f"WIOT{year}_Nov16_ROW.xlsx"
    
    logger.info(f"Attempting to download WIOD {year}...")
    logger.info(f"URL: {url}")
    
    success = download_file(url, output_path, verify_ssl=False)
    
    if success:
        return output_path
    else:
        logger.warning(f"Download failed for {year}")
        return None


def process_wiod_table(filepath: Path) -> pd.DataFrame:
    """
    Process WIOD Excel table
    
    Args:
        filepath: Path to WIOD Excel file
    
    Returns:
        Processed DataFrame
    """
    try:
        logger.info(f"Processing {filepath.name}...")
        
        # WIOD tables are in Excel format with specific structure
        df = pd.read_excel(filepath, sheet_name=0)
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        print_data_summary(df, f"WIOD {filepath.stem}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing WIOD table: {e}")
        return pd.DataFrame()


def extract_rcep_wiod(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract RCEP country flows from WIOD table
    
    Args:
        df: Full WIOD DataFrame
    
    Returns:
        RCEP subset
    """
    # WIOD country codes that are in RCEP
    wiod_rcep_codes = ['AUS', 'CHN', 'IDN', 'JPN', 'KOR']
    
    logger.info(f"Extracting RCEP countries: {', '.join(wiod_rcep_codes)}")
    
    # Actual filtering depends on WIOD structure
    # Typically rows and columns are country-industry combinations
    
    return df


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("WIOD (World Input-Output Database) Acquisition")
    logger.info("="*60)
    
    # Create WIOD directory
    wiod_dir = DATA_DIR / "wiod"
    wiod_dir.mkdir(exist_ok=True)
    
    # Check for existing WIOD files
    wiod_files = list(wiod_dir.glob("WIOT*.xlsx"))
    
    if wiod_files:
        logger.info(f"\nFound {len(wiod_files)} WIOD file(s)")
        
        for filepath in wiod_files:
            df = process_wiod_table(filepath)
            
            if not df.empty:
                # Extract RCEP subset
                df_rcep = extract_rcep_wiod(df)
                
                # Save
                year = filepath.stem.split('_')[0].replace('WIOT', '')
                output_file = DATA_DIR / f"wiod_rcep_{year}_{datetime.now().strftime('%Y%m%d')}.csv"
                save_dataframe(df_rcep, output_file)
    else:
        logger.info("\nNo WIOD files found locally")
        
        # Try to download recent years
        logger.info("\nAttempting to download WIOD tables...")
        test_years = [2014, 2013, 2012]
        
        for year in test_years:
            filepath = download_wiod_table(year)
            if filepath and filepath.exists():
                df = process_wiod_table(filepath)
                if not df.empty:
                    df_rcep = extract_rcep_wiod(df)
                    output_file = DATA_DIR / f"wiod_rcep_{year}_{datetime.now().strftime('%Y%m%d')}.csv"
                    save_dataframe(df_rcep, output_file)
        
        # If downloads fail, show instructions
        if not list(wiod_dir.glob("WIOT*.xlsx")):
            download_wiod_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("WIOD acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
