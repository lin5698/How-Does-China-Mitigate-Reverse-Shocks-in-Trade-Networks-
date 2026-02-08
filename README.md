# RCEP Trade Data Acquisition Framework

This repository contains a comprehensive suite of Python scripts to acquire, process, and analyze trade data for RCEP member countries. The framework supports multi-layer network analysis at country, industry, and product levels.

## 📂 Project Structure

```
data_acquisition/
├── data/                   # Data storage directory (gitignored)
├── config.py               # Configuration (countries, API keys, paths)
├── utils.py                # Shared utilities for requests and I/O
├── 01_comtrade_bilateral.py # UN Comtrade bilateral trade flows
├── 02_wits_trade.py        # WITS trade data (manual download helper)
├── 03_oecd_tiva_trade.py   # OECD TiVA bilateral service trade
├── 04_cepii_gravity.py     # CEPII Gravity database (distance, RTA, etc.)
├── 05_wits_tariffs.py      # WITS/UNCTAD tariff data
├── 07_worldbank_tariffs.py # World Bank WDI tariff indicators
├── 08_oecd_icio.py         # OECD Inter-Country Input-Output tables
├── 09_wiod.py              # World Input-Output Database
├── 10_adb_mrio.py          # ADB Multi-Regional Input-Output tables
├── 11_oecd_tiva_gvc.py     # OECD TiVA GVC indicators
├── 12_gvc_indices.py       # GVC participation & complementarity metrics
├── 13_country_network.py   # Country-level network construction
├── 14_industry_network.py  # Industry-level network construction
└── 15_product_network.py   # Product-level network framework
```

## 🚀 Getting Started

### 1. Prerequisites

Install the required Python packages:

```bash
pip install -r ../requirements.txt
```

### 2. API Configuration

Copy `.env.example` to `.env` and add your API keys:

```bash
cp ../.env.example ../.env
```

Required keys:
- **UN Comtrade**: Register at [comtradeplus.un.org](https://comtradeplus.un.org/)
- **WITS**: Register at [wits.worldbank.org](https://wits.worldbank.org/) (mostly for manual download)
- **OECD**: Optional, public access available

### 3. Data Acquisition Workflow

The scripts are numbered to suggest a logical execution order:

1.  **Bilateral Trade**: Run `01_comtrade_bilateral.py` to fetch trade flows.
2.  **Gravity Data**: Run `04_cepii_gravity.py` to get distance and contiguity data.
3.  **Tariffs**: Run `07_worldbank_tariffs.py` for macro indicators. Use `05_wits_tariffs.py` for instructions on detailed tariff downloads.
4.  **Input-Output**: Run `08_oecd_icio.py` or `10_adb_mrio.py` depending on your focus (ADB has better Asian coverage).
5.  **GVC Indicators**: Run `11_oecd_tiva_gvc.py` to get value-added trade metrics.

### 4. Network Construction

After acquiring data, generate networks:

- **Country Network**: `13_country_network.py` aggregates trade flows into a weighted directed graph.
- **Industry Network**: `14_industry_network.py` uses IO tables to create cross-industry linkages.
- **Product Network**: `15_product_network.py` (advanced) for detailed product space analysis.

## 📊 Data Sources

| Data Type | Primary Source | Script | Notes |
|-----------|----------------|--------|-------|
| **Bilateral Trade** | UN Comtrade | `01` | API rate limited; supports bulk download |
| **Tariffs** | WITS / UNCTAD | `05` | Mostly manual download required |
| **Macro Indicators** | World Bank WDI | `03`, `07` | Supports API or **Kaggle `WDIData.csv`** |
| **Services Trade** | OECD TiVA | `03` | Good for value-added services |
| **Input-Output** | OECD ICIO / ADB | `08`, `10` | Large files; ADB covers more Asian LDCs |
| **GVC Metrics** | OECD TiVA | `11` | Forward/Backward participation indices |
| **Gravity Vars** | CEPII | `04` | Distance, language, colonial history |

## ⚠️ Important Notes

- **Kaggle WDI Dataset**: You can download the [World Development Indicators](https://www.kaggle.com/datasets/umitka/world-development-indicators) dataset from Kaggle. Place the `WDIData.csv` file in `data_acquisition/data/` and the scripts will automatically use it instead of the API.
- **Manual Downloads**: Many international databases (WITS, OECD ICIO) restrict API access for bulk data. The scripts provide detailed instructions for manual downloads when APIs fail.
- **Data Storage**: Large files (IO tables) are stored in `data/` which should not be committed to version control.
- **SSL Issues**: Some legacy servers (CEPII) may have SSL certificate issues. Scripts include fallback mechanisms.

## 📈 Network Analysis

The network scripts use `NetworkX` to calculate:
- **Degree Centrality**: Trade hub identification
- **PageRank**: Economic influence
- **Community Detection**: Trade blocs
- **GVC Position**: Upstream vs. Downstream integration
