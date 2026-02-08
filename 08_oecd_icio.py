"""
OECD ICIO (Inter-Country Input-Output) Tables
Downloads and processes OECD input-output tables

Website: https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm
Data: https://stats.oecd.org/
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR
from utils import save_dataframe, download_file, logger, print_data_summary


def download_oecd_icio_instructions():
    """
    Provide instructions for downloading OECD ICIO tables
    """
    logger.info("\n" + "="*60)
    logger.info("OECD ICIO DOWNLOAD INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\nOECD ICIO tables are large files (100+ MB) and require manual download:")
    
    logger.info("\nOption 1: Direct Download")
    logger.info("1. Visit: https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm")
    logger.info("2. Click on 'Download ICIO tables'")
    logger.info("3. Choose the latest edition (2021 or newer)")
    logger.info("4. Download the full ICIO table (CSV or Excel format)")
    logger.info(f"5. Save to: {DATA_DIR}/oecd_icio_[year].csv")
    
    logger.info("\nOption 2: OECD.Stat")
    logger.info("1. Go to: https://stats.oecd.org/")
    logger.info("2. Search for 'ICIO' or 'Inter-Country Input-Output'")
    logger.info("3. Select 'OECD Inter-Country Input-Output Database'")
    logger.info("4. Choose dimensions:")
    logger.info("   - Countries: Select RCEP members")
    logger.info("   - Industries: All industries or specific sectors")
    logger.info("   - Year: Latest available")
    logger.info("5. Export as CSV")
    
    logger.info("\nICIO Table Structure:")
    logger.info("- Rows: Country-Industry combinations (e.g., CHN_C01)")
    logger.info("- Columns: Country-Industry combinations + Final Demand")
    logger.info("- Values: Intermediate inputs in millions USD")
    
    logger.info("\nRCEP Countries in OECD ICIO:")
    rcep_in_oecd = ['AUS', 'CHN', 'IDN', 'JPN', 'KOR', 'MYS', 'NZL', 'PHL', 'SGP', 'THA', 'VNM']
    for code in rcep_in_oecd:
        logger.info(f"  {code}: {RCEP_COUNTRIES.get(code, 'Unknown')}")
    
    logger.info("\nNote: Not all RCEP countries are in OECD ICIO")
    logger.info("Missing: BRN, KHM, LAO, MMR (aggregated in 'Rest of World')")
    
    logger.info("\n" + "="*60)


def process_oecd_icio_file(filepath: Path) -> pd.DataFrame:
    """
    Process downloaded OECD ICIO file
    
    Args:
        filepath: Path to ICIO CSV file
    
    Returns:
        Processed DataFrame
    """
    try:
        logger.info(f"Loading OECD ICIO from {filepath}...")
        logger.info("This may take a while (large file)...")
        
        df = pd.read_csv(filepath, low_memory=False)
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        
        # Filter for RCEP countries if needed
        # ICIO format: rows are country-industry, columns are country-industry
        # This is a simplified filter - actual processing depends on file structure
        
        print_data_summary(df, "OECD ICIO")
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing OECD ICIO: {e}")
        return pd.DataFrame()


def extract_rcep_icio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract RCEP country flows from full ICIO table
    
    Args:
        df: Full ICIO DataFrame
    
    Returns:
        RCEP-only subset
    """
    # This is a placeholder - actual extraction depends on ICIO structure
    # Typically need to filter both rows and columns for RCEP countries
    
    rcep_codes = ['AUS', 'CHN', 'IDN', 'JPN', 'KOR', 'MYS', 'NZL', 'PHL', 'SGP', 'THA', 'VNM']
    
    logger.info("Extracting RCEP subset from ICIO...")
    logger.info(f"Looking for countries: {', '.join(rcep_codes)}")
    
    # Actual filtering would be done here based on column/row names
    # Example: df_rcep = df[df['Country'].isin(rcep_codes)]
    
    return df


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("OECD ICIO Table Acquisition")
    logger.info("="*60)
    
    # Check for existing ICIO files
    icio_files = list(DATA_DIR.glob("oecd_icio*.csv")) + \
                 list(DATA_DIR.glob("ICIO*.csv"))
    
    if icio_files:
        logger.info(f"\nFound {len(icio_files)} ICIO file(s)")
        
        for filepath in icio_files:
            df = process_oecd_icio_file(filepath)
            
            if not df.empty:
                # Extract RCEP subset
                df_rcep = extract_rcep_icio(df)
                
                # Save processed data
                output_file = DATA_DIR / f"oecd_icio_rcep_{datetime.now().strftime('%Y%m%d')}.csv"
                save_dataframe(df_rcep, output_file)
    else:
        logger.info("\nNo OECD ICIO files found")
        download_oecd_icio_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("OECD ICIO acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
