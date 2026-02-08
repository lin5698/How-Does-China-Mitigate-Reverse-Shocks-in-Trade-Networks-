"""
OECD TiVA Global Value Chain Indicators
Fetches domestic/foreign value-added trade flows by industry

Indicators include:
- EXGR: Gross exports by industry and partner
- EXGR_FVA: Foreign value added content of gross exports
- EXGR_DVA: Domestic value added content of gross exports
- FD_VA: Value added in final demand
"""

import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent))
from config import RCEP_COUNTRIES, DATA_DIR
from utils import save_dataframe, logger, print_data_summary


def download_oecd_tiva_gvc_instructions():
    """
    Provide instructions for downloading OECD TiVA GVC indicators
    """
    logger.info("\n" + "="*60)
    logger.info("OECD TiVA GVC INDICATORS DOWNLOAD")
    logger.info("="*60)
    
    logger.info("\nOECD TiVA provides comprehensive GVC participation metrics:")
    
    logger.info("\nKey Indicators to Download:")
    logger.info("1. EXGR - Gross exports by industry and partner")
    logger.info("2. EXGR_FVA - Foreign value added in gross exports")
    logger.info("3. EXGR_DVA - Domestic value added in gross exports")
    logger.info("4. EXGR_DDC - Domestic value added re-imported")
    logger.info("5. FD_VA - Value added embodied in final demand")
    logger.info("6. IMGR_FVA - Foreign value added in imports")
    
    logger.info("\nDownload Steps:")
    logger.info("1. Visit: https://stats.oecd.org/")
    logger.info("2. Search for 'TiVA' or navigate to Trade > TiVA")
    logger.info("3. Select 'TiVA 2021 Principal Indicators'")
    logger.info("4. Choose dimensions:")
    logger.info("   - Country: Select all RCEP countries")
    logger.info("   - Partner: Select all RCEP countries")
    logger.info("   - Industry: All industries or specific sectors")
    logger.info("   - Indicator: Select GVC indicators listed above")
    logger.info("   - Year: Latest available (usually 2018)")
    logger.info("5. Export as CSV")
    logger.info(f"6. Save to: {DATA_DIR}/oecd_tiva_gvc_indicators.csv")
    
    logger.info("\nAlternative: OECD Data Explorer")
    logger.info("https://data-explorer.oecd.org/")
    logger.info("Navigate to: Trade > Trade in Value Added (TiVA) > Principal Indicators")
    
    logger.info("\nRCEP Countries in OECD TiVA:")
    tiva_rcep = ['AUS', 'CHN', 'IDN', 'JPN', 'KOR', 'MYS', 'NZL', 'PHL', 'SGP', 'THA', 'VNM']
    for code in tiva_rcep:
        logger.info(f"  {code}: {RCEP_COUNTRIES.get(code, 'Unknown')}")
    
    logger.info("\nNote: BRN, KHM, LAO, MMR not in OECD TiVA")
    
    logger.info("\n" + "="*60)


def process_tiva_gvc_file(filepath: Path) -> pd.DataFrame:
    """
    Process downloaded OECD TiVA GVC indicators file
    
    Args:
        filepath: Path to TiVA GVC CSV file
    
    Returns:
        Processed DataFrame
    """
    try:
        logger.info(f"Loading OECD TiVA GVC indicators from {filepath}...")
        
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} rows")
        
        # Filter for RCEP countries
        rcep_codes = list(RCEP_COUNTRIES.keys())
        
        if 'Country' in df.columns and 'Partner' in df.columns:
            df = df[
                (df['Country'].isin(rcep_codes)) & 
                (df['Partner'].isin(rcep_codes))
            ]
            logger.info(f"Filtered to {len(df)} RCEP bilateral observations")
        
        print_data_summary(df, "OECD TiVA GVC Indicators")
        
        return df
        
    except Exception as e:
        logger.error(f"Error processing TiVA GVC file: {e}")
        return pd.DataFrame()


def calculate_gvc_participation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate forward and backward GVC participation indices
    
    Args:
        df: TiVA data with DVA and FVA indicators
    
    Returns:
        DataFrame with GVC participation metrics
    """
    logger.info("Calculating GVC participation indices...")
    
    # Forward participation: DVA in partners' exports
    # Backward participation: FVA in own exports
    # Total participation = Forward + Backward
    
    # This is a simplified calculation - actual implementation depends on data structure
    
    results = []
    
    # Group by country and year
    if 'Country' in df.columns and 'Year' in df.columns:
        for (country, year), group in df.groupby(['Country', 'Year']):
            
            # Calculate metrics (simplified)
            fva = group[group['Indicator'] == 'EXGR_FVA']['Value'].sum() if 'EXGR_FVA' in group['Indicator'].values else 0
            dva = group[group['Indicator'] == 'EXGR_DVA']['Value'].sum() if 'EXGR_DVA' in group['Indicator'].values else 0
            gross_exports = group[group['Indicator'] == 'EXGR']['Value'].sum() if 'EXGR' in group['Indicator'].values else 0
            
            if gross_exports > 0:
                backward_participation = fva / gross_exports
                forward_participation = dva / gross_exports
                total_participation = backward_participation + forward_participation
                
                results.append({
                    'Country': country,
                    'Year': year,
                    'Backward_GVC_Participation': backward_participation,
                    'Forward_GVC_Participation': forward_participation,
                    'Total_GVC_Participation': total_participation,
                    'Gross_Exports': gross_exports,
                    'Foreign_VA': fva,
                    'Domestic_VA': dva
                })
    
    if results:
        result_df = pd.DataFrame(results)
        print_data_summary(result_df, "GVC Participation Indices")
        return result_df
    
    return pd.DataFrame()


def main():
    """Main execution function"""
    logger.info("="*60)
    logger.info("OECD TiVA GVC Indicators Acquisition")
    logger.info("="*60)
    
    # Check for existing files
    gvc_files = list(DATA_DIR.glob("*tiva*gvc*.csv")) + \
                list(DATA_DIR.glob("*tiva*indicator*.csv"))
    
    if gvc_files:
        logger.info(f"\nFound {len(gvc_files)} TiVA GVC file(s)")
        
        for filepath in gvc_files:
            df = process_tiva_gvc_file(filepath)
            
            if not df.empty:
                # Save processed data
                output_file = DATA_DIR / f"oecd_tiva_gvc_processed_{datetime.now().strftime('%Y%m%d')}.csv"
                save_dataframe(df, output_file)
                
                # Calculate GVC participation indices
                gvc_indices = calculate_gvc_participation(df)
                
                if not gvc_indices.empty:
                    indices_file = DATA_DIR / f"gvc_participation_indices_{datetime.now().strftime('%Y%m%d')}.csv"
                    save_dataframe(gvc_indices, indices_file)
    else:
        logger.info("\nNo TiVA GVC files found")
        download_oecd_tiva_gvc_instructions()
    
    logger.info("\n" + "="*60)
    logger.info("OECD TiVA GVC acquisition complete")
    logger.info("="*60)


if __name__ == "__main__":
    main()
