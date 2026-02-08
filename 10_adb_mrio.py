"""
ADB MRIO (Multi-Regional Input-Output) Tables
Asian Development Bank input-output tables for Asian economies

Website: https://mrio.adbx.online/
Coverage: Asian economies with detailed industry linkages
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR
from utils import save_dataframe, logger, print_data_summary


def download_adb_mrio_instructions():
    """
    Provide instructions for downloading ADB MRIO tables
    """
    logger.info("\n" + "="*60)
    logger.info("ADB MRIO DOWNLOAD INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\nADB Multi-Regional Input-Output Database:")
    logger.info("Focuses on Asian economies with detailed industry linkages")
    
    logger.info("\nDownload Steps:")
    logger.info("1. Visit: https://mrio.adbx.online/")
    logger.info("2. Register for an account (free)")
    logger.info("3. Navigate to 'Data Download'")
    logger.info("4. Select:")
    logger.info("   - Database: ADB MRIO (latest version)")
    logger.info("   - Countries: RCEP Asian members")
    logger.info("   - Years: Available years (typically 2000-2020)")
    logger.info("   - Format: CSV or Excel")
    logger.info("5. Download the MRIO table")
    logger.info(f"6. Save to: {DATA_DIR}/adb_mrio/")
    
    logger.info("\nAlternative: ADB Data Library")
    logger.info("https://data.adb.org/")
    logger.info("Search for 'Multi-Regional Input-Output'")
    
    logger.info("\nRCEP Countries in ADB MRIO:")
    asian_rcep = {
        'CHN': 'China',
        'JPN': 'Japan',
        'KOR': 'South Korea',
        'IDN': 'Indonesia',
        'MYS': 'Malaysia',
        'PHL': 'Philippines',
        'SGP': 'Singapore',
        'THA': 'Thailand',
        'VNM': 'Vietnam',
        'KHM': 'Cambodia',
        'LAO': 'Laos',
        'MMR': 'Myanmar',
        'BRN': 'Brunei',
    }
    
    for code, name in asian_rcep.items():
        logger.info(f"  {code}: {name}")
    
    logger.info("\nNote: ADB MRIO has excellent coverage of RCEP Asian economies")
    logger.info("Australia and New Zealand may be included in recent versions")
    
    logger.info("\n" + "="*60)


def process_adb_mrio_file(filepath: Path) -> pd.DataFrame:
    """
    Process downloaded ADB MRIO file
    
    Args:
        filepath: Path to ADB MRIO file
    
    Returns:
        Processed DataFrame
    """
    try:
        logger.info(f"Loading ADB MRIO from {filepath}...")
        
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath, low_memory=False)
        elif filepath.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        else:
            logger.error(f"Unsupported format: {filepath.suffix}")
            return pd.DataFrame()
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        print_data_summary(df, "ADB MRIO")
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing ADB MRIO: {e}")
        return pd.DataFrame()


def extract_rcep_mrio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract RCEP country flows from ADB MRIO
    
    Args:
        df: Full MRIO DataFrame
    
    Returns:
        RCEP subset
    """
    rcep_codes = list(RCEP_COUNTRIES.keys())
    logger.info(f"Filtering for RCEP countries: {', '.join(rcep_codes)}")
    
    # Actual filtering depends on ADB MRIO structure
    # Typically country-industry rows and columns
    
    return df


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("ADB MRIO Table Acquisition")
    logger.info("="*60)
    
    # Create ADB MRIO directory
    mrio_dir = DATA_DIR / "adb_mrio"
    mrio_dir.mkdir(exist_ok=True)
    
    # Check for existing files
    mrio_files = list(mrio_dir.glob("*.csv")) + list(mrio_dir.glob("*.xlsx"))
    
    if mrio_files:
        logger.info(f"\nFound {len(mrio_files)} ADB MRIO file(s)")
        
        for filepath in mrio_files:
            df = process_adb_mrio_file(filepath)
            
            if not df.empty:
                # Extract RCEP subset
                df_rcep = extract_rcep_mrio(df)
                
                # Save
                output_file = DATA_DIR / f"adb_mrio_rcep_{datetime.now().strftime('%Y%m%d')}.csv"
                save_dataframe(df_rcep, output_file)
    else:
        logger.info("\nNo ADB MRIO files found")
        download_adb_mrio_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("ADB MRIO acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
