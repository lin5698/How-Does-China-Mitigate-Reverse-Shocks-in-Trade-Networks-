"""
CEPII Gravity Database Acquisition
Downloads bilateral trade data with gravity model variables

Website: http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele.asp
Direct download: http://www.cepii.fr/DATA_DOWNLOAD/gravity/data/
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime
import zipfile

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR, CEPII_GRAVITY_URL
from utils import download_file, save_dataframe, logger, print_data_summary


def download_cepii_gravity() -> Path:
    """
    Download CEPII Gravity database
    
    Returns:
        Path to downloaded file or None if failed
    """
    logger.info("Downloading CEPII Gravity database...")
    logger.info(f"URL: {CEPII_GRAVITY_URL}")
    
    output_path = DATA_DIR / "Gravity_V202211.zip"
    
    # CEPII often has SSL issues, so verify_ssl=False
    success = download_file(CEPII_GRAVITY_URL, output_path, verify_ssl=False)
    
    if success:
        return output_path
    else:
        logger.error("Download failed")
        return None


def extract_and_process_gravity(zip_path: Path) -> pd.DataFrame:
    """
    Extract and process CEPII Gravity data
    
    Args:
        zip_path: Path to downloaded ZIP file
    
    Returns:
        Processed DataFrame with RCEP bilateral trade
    """
    try:
        logger.info(f"Extracting {zip_path}...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to data directory
            extract_dir = DATA_DIR / "cepii_gravity"
            extract_dir.mkdir(exist_ok=True)
            zip_ref.extractall(extract_dir)
            
            logger.info(f"Extracted to {extract_dir}")
            
            # Find the main data file (usually Gravity_V202211.csv or similar)
            csv_files = list(extract_dir.glob("*.csv"))
            
            if not csv_files:
                logger.error("No CSV files found in archive")
                return pd.DataFrame()
            
            # Load the main gravity file
            main_file = csv_files[0]
            logger.info(f"Loading {main_file}...")
            
            df = pd.read_csv(main_file, low_memory=False)
            logger.info(f"Loaded {len(df)} rows")
            
            # Filter for RCEP countries
            rcep_codes = list(RCEP_COUNTRIES.keys())
            
            # CEPII uses iso3 codes
            df_rcep = df[
                (df['iso3_o'].isin(rcep_codes)) & 
                (df['iso3_d'].isin(rcep_codes))
            ].copy()
            
            logger.info(f"Filtered to {len(df_rcep)} RCEP bilateral observations")
            
            print_data_summary(df_rcep, "CEPII Gravity (RCEP)")
            
            return df_rcep
            
    except Exception as e:
        logger.error(f"Error processing CEPII Gravity: {e}")
        return pd.DataFrame()


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("CEPII Gravity Database Acquisition")
    logger.info("="*60)
    
    # Check if already downloaded
    existing_zip = DATA_DIR / "Gravity_V202211.zip"
    
    if existing_zip.exists():
        logger.info(f"Found existing download: {existing_zip}")
        zip_path = existing_zip
    else:
        # Download
        zip_path = download_cepii_gravity()
    
    if zip_path and zip_path.exists():
        # Extract and process
        df = extract_and_process_gravity(zip_path)
        
        if not df.empty:
            # Save processed RCEP data
            output_file = DATA_DIR / f"cepii_gravity_rcep_{datetime.now().strftime('%Y%m%d')}.csv"
            save_dataframe(df, output_file)
            
            logger.info("\nKey variables in CEPII Gravity:")
            logger.info("- tradeflow_baci: Bilateral trade flows")
            logger.info("- dist: Distance between countries")
            logger.info("- contig: Contiguity (shared border)")
            logger.info("- comlang_off: Common official language")
            logger.info("- rta: Regional Trade Agreement")
            logger.info("- comcur: Common currency")
    else:
        logger.error("Failed to download CEPII Gravity database")
        logger.info("\nMANUAL DOWNLOAD:")
        logger.info("1. Visit: http://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele.asp")
        logger.info("2. Navigate to 'Gravity' database")
        logger.info("3. Download the latest version (ZIP file)")
        logger.info(f"4. Save to: {DATA_DIR}/")
        logger.info("5. Run this script again")
    
    logger.info("\n" + "="*60)
    logger.info("CEPII Gravity acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
