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


## 🧠 Network-TVP-VAR + Counterfactual Model (RCEP Reverse-Shock Resilience)

This repo now includes an executable research script: `16_network_tvp_var_counterfactual.py`.

It operationalizes the methodology in the paper draft:
- Quarterly VAX proxy construction with annual benchmarking
- Rolling network matrix construction (`W_t`) with smoothing
- Country-level time-varying coefficients (`a_own`, `b_net`) via rolling ridge estimation
- Low-rank compression for network coefficients (CP-style approximation)
- Counterfactual decomposition (`Total` vs `Direct`, with `B=0`) and amplification share
- Rolling forecast evaluation (`h=1`, `h=4`) vs AR(1)/no-network baselines

Run:

```bash
python 16_network_tvp_var_counterfactual.py
```

Outputs are saved to `data/model_outputs/`:
- `tvp_country_coefficients.csv`
- `cp_compressed_network_coefficients.csv`
- `counterfactual_amplification_panel.csv`
- `rolling_forecast_evaluation.csv`
- `model_run_summary.json`


## 🧩 Step 0 Quarterly Panel Alignment (2000Q1–2023Q4)

Use `00_quarterly_alignment.py` to enforce a unified quarter index and country coding for all RCEP members.

```bash
python 00_quarterly_alignment.py
```

What it does:
- builds a master quarter index (`2000Q1`–`2023Q4`)
- aligns macro panel to `15 countries × 96 quarters`
- aligns bilateral panel to `15 × 15 country-pairs × 96 quarters`
- applies fixed frequency-conversion rules (monthly flow=sum, index=mean, eop=quarter-end) via reusable helper functions
- exports missingness matrices and a breakpoint-log template for documentation

Output directory: `data/alignment/`
- `quarter_master_index.csv`
- `rcep_macro_aligned_2000Q1_2023Q4.csv`
- `rcep_bilateral_aligned_2000Q1_2023Q4.csv`
- `macro_missing_matrix.csv`
- `bilateral_missing_matrix.csv`
- `alignment_validation_report.csv`
- `breakpoint_log_template.csv`


## 📄 Main Text Figures & Tables (Figure 1-3, Table 1-2 + Appendix A1-A6)

Generate manuscript-ready artifacts with:

```bash
python 17_generate_paper_figures_tables.py
```

Output directory: `data/paper_outputs/`
- Main text:
  - `Figure1_tariff_path.svg`
  - `Figure2_amplification_timeseries.svg`
  - `Figure3_absorber_pre_post_top10.svg`
  - `table1_baseline_fe.csv`
  - `table2_rolling_cv.csv`
- Appendix support (CSV + chart):
  - `A1_indicator_alternatives.csv` + `A1_indicator_alternatives.svg`
  - `A2_W_sensitivity.csv` + `A2_W_sensitivity.svg`
  - `A3_rank_lag_robustness.csv` + `A3_rank_lag_robustness.svg`
  - `A4_placebo_dates.csv` + `A4_placebo_dates.svg`
  - `A5_crisis_exclusion.csv` + `A5_crisis_exclusion.svg`
  - `A6_tvp_girf_surface_data.csv` + `A6_tvp_girf_surface_heatmap.svg`
