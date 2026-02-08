"""
Configuration file for RCEP trade data acquisition
Contains country codes, API settings, and data parameters
"""

import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data_acquisition" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# RCEP Member Countries (ISO3 codes)
RCEP_COUNTRIES = {
    'AUS': 'Australia',
    'BRN': 'Brunei',
    'KHM': 'Cambodia',
    'CHN': 'China',
    'IDN': 'Indonesia',
    'JPN': 'Japan',
    'KOR': 'South Korea',
    'LAO': 'Laos',
    'MYS': 'Malaysia',
    'MMR': 'Myanmar',
    'NZL': 'New Zealand',
    'PHL': 'Philippines',
    'SGP': 'Singapore',
    'THA': 'Thailand',
    'VNM': 'Vietnam'
}

# ISO2 codes for some APIs
RCEP_ISO2 = {
    'AU': 'Australia',
    'BN': 'Brunei',
    'KH': 'Cambodia',
    'CN': 'China',
    'ID': 'Indonesia',
    'JP': 'Japan',
    'KR': 'South Korea',
    'LA': 'Laos',
    'MY': 'Malaysia',
    'MM': 'Myanmar',
    'NZ': 'New Zealand',
    'PH': 'Philippines',
    'SG': 'Singapore',
    'TH': 'Thailand',
    'VN': 'Vietnam'
}

# Belt and Road Initiative (BRI) Major Partners (Representative List)
# Based on major trade partners along the routes
BRI_COUNTRIES = {
    # Southeast Asia (ASEAN) - overlapping with RCEP
    'SGP': 'Singapore', 'IDN': 'Indonesia', 'MYS': 'Malaysia', 'THA': 'Thailand', 
    'VNM': 'Vietnam', 'PHL': 'Philippines', 'KHM': 'Cambodia', 'LAO': 'Laos', 
    'MMR': 'Myanmar', 'BRN': 'Brunei',
    
    # South Asia
    'PAK': 'Pakistan', 'BGD': 'Bangladesh', 'LKA': 'Sri Lanka', 'NPL': 'Nepal',
    
    # Central Asia
    'KAZ': 'Kazakhstan', 'UZB': 'Uzbekistan', 'KGZ': 'Kyrgyzstan', 
    'TJK': 'Tajikistan', 'TKM': 'Turkmenistan',
    
    # West Asia / Middle East
    'IRN': 'Iran', 'TUR': 'Turkey', 'SAU': 'Saudi Arabia', 'ARE': 'United Arab Emirates',
    'ISR': 'Israel', 'QAT': 'Qatar', 'KWT': 'Kuwait', 'IRQ': 'Iraq',
    
    # Europe (Eastern/Central)
    'RUS': 'Russia', 'POL': 'Poland', 'HUN': 'Hungary', 'CZE': 'Czech Republic',
    'SVK': 'Slovakia', 'GRC': 'Greece', 'SRB': 'Serbia',
    
    # Africa
    'EGY': 'Egypt', 'ZAF': 'South Africa', 'ETH': 'Ethiopia', 'KEN': 'Kenya',
    'NGA': 'Nigeria', 'DZA': 'Algeria',
    
    # Latin America (Extended)
    'BRA': 'Brazil', 'ARG': 'Argentina', 'CHL': 'Chile', 'PER': 'Peru'
}

# ISO2 codes for BRI countries (subset for API mapping)
# Will be generated dynamically in utils if needed, or we can map common ones here
BRI_ISO2 = {
    'PK': 'Pakistan', 'BD': 'Bangladesh', 'LK': 'Sri Lanka',
    'KZ': 'Kazakhstan', 'UZ': 'Uzbekistan',
    'RU': 'Russia', 'TR': 'Turkey', 'IR': 'Iran',
    'EG': 'Egypt', 'ZA': 'South Africa'
}

# Time periods
START_YEAR = 2005
END_YEAR = 2024
RECENT_YEAR = 2023

# API Keys (set via environment variables or .env file)
COMTRADE_API_KEY = os.getenv('COMTRADE_API_KEY', '')
WITS_API_KEY = os.getenv('WITS_API_KEY', '')
OECD_API_KEY = os.getenv('OECD_API_KEY', '')
WB_API_KEY = os.getenv('WB_API_KEY', '')  # World Bank (optional, usually open)

# API endpoints
COMTRADE_API_URL = "https://comtradeapi.un.org/data/v1/get"
OECD_API_URL = "https://stats.oecd.org/restsdmx/sdmx.ashx/GetData"
CEPII_GRAVITY_URL = "http://www.cepii.fr/DATA_DOWNLOAD/gravity/data/Gravity_V202211.zip"
WIOD_URL = "https://www.rug.nl/ggdc/valuechain/wiod/"
ADB_MRIO_URL = "https://mrio.adbx.online/"
WITS_API_URL = "http://wits.worldbank.org/API/V1/SDMX/V21"

# HS Classification levels
HS_LEVELS = {
    'HS2': 2,   # Chapter level (99 chapters)
    'HS4': 4,   # Heading level (~1,200 headings)
    'HS6': 6    # Subheading level (~5,000 subheadings)
}

# Macro & Tariff Data Configuration
MACRO_INDICATORS = {
    'GDP_GROWTH': 'NY.GDP.MKTP.KD.ZG',   # GDP growth (annual %)
    'GDP_CURRENT': 'NY.GDP.MKTP.CD',     # GDP (current US$)
    'REER': 'PX.REX.REER',               # Real effective exchange rate index
    'INFLATION': 'FP.CPI.TOTL.ZG',       # Inflation, consumer prices (annual %)
    'TRADE_GDP': 'NE.TRD.GNFS.ZS'        # Trade (% of GDP)
}

TARIFF_INDICATORS = {
    'MFN_WEIGHTED': 'TM.TAX.MRCH.WM.AR.ZS',   # Tariff rate, most favored nation, weighted mean, all products (%)
    'APPLIED_WEIGHTED': 'TM.TAX.MRCH.WM.FN.ZS' # Tariff rate, applied, weighted mean, all products (%)
}

# ISIC/Industry classifications
ISIC_REV4_SECTORS = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J',
    'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U'
]

# Request settings
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1.0  # seconds between requests
COMTRADE_RATE_LIMIT_DELAY = 6.0 # Comtrade free tier is strict (1 request per 6s usually)

# Data quality thresholds
MIN_TRADE_VALUE = 1000  # USD, filter out very small flows
MIN_COVERAGE_YEARS = 5  # Minimum years of data required

# Network parameters
NETWORK_WEIGHT_THRESHOLD = 0.01  # Minimum edge weight (as fraction of total trade)
NETWORK_TYPES = ['country', 'industry', 'product']

# Output formats
OUTPUT_FORMATS = ['csv', 'parquet', 'excel']
DEFAULT_FORMAT = 'csv'

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = DATA_DIR / 'acquisition.log'

print(f"Configuration loaded. Data directory: {DATA_DIR}")
