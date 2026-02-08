"""
Eora Global Supply Chain Database (MRIO) Acquisition
Fetches or guides acquisition of high-resolution MRIO data from WorldMRIO.com

Website: https://worldmrio.com/
Coverage: 190 countries, detailed industry sectors
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR
from utils import save_dataframe, logger, print_data_summary

def download_eora_instructions():
    """
    Provide instructions for downloading Eora MRIO tables
    """
    logger.info("\n" + "="*60)
    logger.info("EORA MRIO DOWNLOAD INSTRUCTIONS")
    logger.info("="*60)
    
    logger.info("\nEora Global Supply Chain Database:")
    logger.info("High-resolution MRIO tables covering 190 countries.")
    
    logger.info("\nDownload Steps:")
    logger.info("1. Visit: https://worldmrio.com/")
    logger.info("2. Register/Login (Academic/Non-commercial use is often free)")
    logger.info("3. Navigate to 'Data' or 'Download'")
    logger.info("4. Select 'Eora26' (aggregated) or 'Eora Full' (high resolution)")
    logger.info("   - Eora26 is easier to handle but less detailed.")
    logger.info("   - Eora Full is very large and complex.")
    logger.info("5. Download the IO table for the desired year (e.g., 2015-2021)")
    logger.info("   - Look for 'Basic Price' tables if available.")
    logger.info(f"6. Save to: {DATA_DIR}/eora_mrio/")
    
    logger.info("\nRCEP Countries in Eora:")
    logger.info("Eora covers ALL RCEP countries, including:")
    rcep_codes = list(RCEP_COUNTRIES.keys())
    logger.info(f"{', '.join(rcep_codes)}")
    
    logger.info("\n" + "="*60)


def process_eora_file(filepath: Path) -> pd.DataFrame:
    """
    Process downloaded Eora MRIO file
    
    Args:
        filepath: Path to Eora file
    
    Returns:
        Processed DataFrame
    """
    try:
        logger.info(f"Loading Eora MRIO from {filepath}...")
        
        # Eora often comes as huge CSVs or specific formats
        # This is a generic loader
        if filepath.suffix == '.csv':
            df = pd.read_csv(filepath, low_memory=False)
        elif filepath.suffix in ['.xlsx', '.xls']:
            df = pd.read_excel(filepath)
        elif filepath.suffix == '.txt':
             df = pd.read_csv(filepath, sep='\t', low_memory=False)
        else:
            logger.error(f"Unsupported format: {filepath.suffix}")
            return pd.DataFrame()
        
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
        print_data_summary(df, "Eora MRIO")
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing Eora MRIO: {e}")
        return pd.DataFrame()


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("Eora MRIO Data Acquisition")
    logger.info("="*60)
    
    # Create Eora directory
    eora_dir = DATA_DIR / "eora_mrio"
    eora_dir.mkdir(exist_ok=True)
    
    # Check for existing files
    eora_files = list(eora_dir.glob("*.csv")) + \
                 list(eora_dir.glob("*.txt")) + \
                 list(eora_dir.glob("*.zip"))
    
    if eora_files:
        logger.info(f"\nFound {len(eora_files)} Eora file(s)")
        
        for filepath in eora_files:
            if filepath.suffix == '.zip':
                logger.info(f"Found zip file: {filepath.name} (please unzip)")
                continue
                
            df = process_eora_file(filepath)
            
            if not df.empty:
                # Save processed version if needed
                # output_file = DATA_DIR / f"eora_processed_{datetime.now().strftime('%Y%m%d')}.csv"
                # save_dataframe(df, output_file)
                pass
    else:
        logger.info("\nNo Eora MRIO files found")
        download_eora_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("Eora acquisition setup complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
