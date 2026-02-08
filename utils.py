"""
Utility functions for data acquisition
"""

import time
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from config import REQUEST_TIMEOUT, MAX_RETRIES, RATE_LIMIT_DELAY, LOG_FILE, LOG_LEVEL

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def make_request(url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None,
                 max_retries: int = MAX_RETRIES, verify_ssl: bool = False) -> Optional[requests.Response]:
    """
    Make HTTP request with retry logic and error handling
    
    Args:
        url: Request URL
        params: Query parameters
        headers: Request headers
        max_retries: Maximum number of retry attempts
        verify_ssl: Whether to verify SSL certificates (set False for problematic endpoints)
    
    Returns:
        Response object or None if failed
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"Request to {url} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                verify=verify_ssl
            )
            response.raise_for_status()
            time.sleep(RATE_LIMIT_DELAY)  # Rate limiting
            return response
            
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL Error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts due to SSL error")
                return None
            time.sleep(2 ** attempt)  # Exponential backoff
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} attempts")
                return None
            time.sleep(2 ** attempt)
    
    return None


def save_dataframe(df: pd.DataFrame, filepath: Path, format: str = 'csv') -> bool:
    """
    Save DataFrame to file in specified format
    
    Args:
        df: DataFrame to save
        filepath: Output file path
        format: Output format ('csv', 'parquet', 'excel')
    
    Returns:
        True if successful, False otherwise
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'csv':
            df.to_csv(filepath, index=False, encoding='utf-8')
        elif format == 'parquet':
            df.to_parquet(filepath, index=False)
        elif format == 'excel':
            df.to_excel(filepath, index=False)
        else:
            logger.error(f"Unsupported format: {format}")
            return False
        
        logger.info(f"Saved {len(df)} rows to {filepath}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving file {filepath}: {e}")
        return False


def load_dataframe(filepath: Path) -> Optional[pd.DataFrame]:
    """
    Load DataFrame from file, auto-detecting format
    
    Args:
        filepath: Input file path
    
    Returns:
        DataFrame or None if failed
    """
    try:
        suffix = filepath.suffix.lower()
        
        if suffix == '.csv':
            return pd.read_csv(filepath)
        elif suffix == '.parquet':
            return pd.read_parquet(filepath)
        elif suffix in ['.xlsx', '.xls']:
            return pd.read_excel(filepath)
        else:
            logger.error(f"Unsupported file format: {suffix}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading file {filepath}: {e}")
        return None


def download_file(url: str, output_path: Path, verify_ssl: bool = False) -> bool:
    """
    Download file from URL
    
    Args:
        url: Download URL
        output_path: Where to save the file
        verify_ssl: Whether to verify SSL certificates
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading from {url}")
        response = requests.get(url, stream=True, verify=verify_ssl, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"Downloaded to {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


def validate_data(df: pd.DataFrame, required_columns: list, name: str = "dataset") -> bool:
    """
    Validate DataFrame has required columns and data
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        name: Dataset name for logging
    
    Returns:
        True if valid, False otherwise
    """
    if df is None or df.empty:
        logger.error(f"{name}: DataFrame is empty or None")
        return False
    
    missing_cols = set(required_columns) - set(df.columns)
    if missing_cols:
        logger.error(f"{name}: Missing required columns: {missing_cols}")
        return False
    
    logger.info(f"{name}: Validation passed ({len(df)} rows, {len(df.columns)} columns)")
    return True


def get_country_pairs(countries: list) -> list:
    """
    Generate all bilateral country pairs
    
    Args:
        countries: List of country codes
    
    Returns:
        List of (reporter, partner) tuples
    """
    pairs = []
    for i, reporter in enumerate(countries):
        for partner in countries:
            if reporter != partner:
                pairs.append((reporter, partner))
    return pairs


def print_data_summary(df: pd.DataFrame, name: str):
    """
    Print summary statistics for a dataset
    
    Args:
        df: DataFrame to summarize
        name: Dataset name
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Summary: {name}")
    logger.info(f"{'='*60}")
    logger.info(f"Rows: {len(df):,}")
    logger.info(f"Columns: {len(df.columns)}")
    logger.info(f"Memory: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
    logger.info(f"Columns: {', '.join(df.columns.tolist())}")
    logger.info(f"{'='*60}\n")

def load_wdi_from_csv(csv_path: Path, indicators: dict, 
                      countries: list = None, 
                      start_year: int = 2010, 
                      end_year: int = 2023) -> pd.DataFrame:
    """
    Load WDI data from Kaggle dataset CSV 'WDIData.csv'
    
    Args:
        csv_path: Path to WDIData.csv
        indicators: Dict mapping {indicator_name: series_code}
        countries: List of country codes (optional)
        start_year: Start year filter
        end_year: End year filter
        
    Returns:
        DataFrame in long format
    """
    try:
        if not csv_path.exists():
            return None
            
        logger.info(f"Loading WDI from {csv_path}...")
        
        # Read header first to identify columns
        # WDI csv is wide: Country Name, Country Code, Indicator Name, Indicator Code, 1960, ...
        df = pd.read_csv(csv_path)
        
        # Filter by country
        if countries:
            df = df[df['Country Code'].isin(countries)]
            
        # Filter by indicator
        series_ids = list(indicators.values())
        df = df[df['Indicator Code'].isin(series_ids)]
        
        # Helper: Clean and rename
        # Find year columns
        id_vars = ['Country Name', 'Country Code', 'Indicator Name', 'Indicator Code']
        value_vars = [c for c in df.columns if str(c).isdigit()] # Kaggle WDI usually has '1960', '1961'...
        
        if not value_vars:
            # Maybe it has YR1960 format?
            value_vars = [c for c in df.columns if c.startswith('19') or c.startswith('20')]
        
        df_long = df.melt(id_vars=id_vars, value_vars=value_vars, 
                          var_name='year', value_name='value')
        
        df_long['year'] = pd.to_numeric(df_long['year'], errors='coerce')
        df_long = df_long.dropna(subset=['year'])
        df_long['year'] = df_long['year'].astype(int)
        
        # Filter years
        df_long = df_long[
            (df_long['year'] >= start_year) & 
            (df_long['year'] <= end_year)
        ]
        
        # Rename standard columns
        df_long = df_long.rename(columns={
            'Country Code': 'country_code',
            'Country Name': 'Country', 
            'Indicator Code': 'series'
        })
        
        # Map friendly names
        inv_map = {v: k for k, v in indicators.items()}
        df_long['indicator_name'] = df_long['series'].map(inv_map)
        
        # Drop empty values
        df_long = df_long.dropna(subset=['value'])
        
        # Return standard columns
        cols = ['country_code', 'Country', 'year', 'indicator_name', 'series', 'value']
        cols = [c for c in cols if c in df_long.columns]
        
        logger.info(f"Loaded {len(df_long)} records from CSV")
        return df_long[cols]
        
    except Exception as e:
        logger.error(f"Error reading WDI CSV: {e}")
        return None
