"""
Step 0: Quarterly panel alignment for RCEP (2000Q1-2023Q4).

Implements a reproducible alignment workflow:
1) Build master quarter index and ISO3 country skeleton.
2) Provide fixed frequency-conversion rules (M->Q, A->Q benchmark-ready).
3) Align existing quarterly macro / bilateral data to full 15-country panel.
4) Export missingness matrix and breakpoint log templates for auditability.

Inputs (expected in repo root):
- master_quarterly_macro_2005_2024.csv
- master_quarterly_bilateral_2005_2024.csv

Outputs:
- data/alignment/rcep_macro_aligned_2000Q1_2023Q4.csv
- data/alignment/rcep_bilateral_aligned_2000Q1_2023Q4.csv
- data/alignment/macro_missing_matrix.csv
- data/alignment/bilateral_missing_matrix.csv
- data/alignment/alignment_validation_report.csv
- data/alignment/breakpoint_log_template.csv
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Literal

import numpy as np
import pandas as pd

from config import RCEP_COUNTRIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "data" / "alignment"
MACRO_IN = ROOT / "master_quarterly_macro_2005_2024.csv"
BILAT_IN = ROOT / "master_quarterly_bilateral_2005_2024.csv"

START = "2000Q1"
END = "2023Q4"
COUNTRIES = sorted(RCEP_COUNTRIES.keys())


def build_master_quarter_axis(start: str = START, end: str = END) -> pd.DataFrame:
    p = pd.period_range(start=start, end=end, freq="Q")
    axis = pd.DataFrame({"quarter": p})
    axis["year"] = axis["quarter"].dt.year
    axis["q"] = axis["quarter"].dt.quarter
    axis["date_start"] = axis["quarter"].dt.start_time
    axis["date_end"] = axis["quarter"].dt.end_time
    return axis


def monthly_to_quarterly(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    group_cols: Iterable[str],
    var_type: Literal["flow", "index", "eop"] = "flow",
) -> pd.DataFrame:
    """Generic M->Q conversion with fixed rules: flow=sum, index=mean, eop=quarter-end."""
    x = df.copy()
    x[date_col] = pd.to_datetime(x[date_col])
    x["quarter"] = x[date_col].dt.to_period("Q")

    if var_type == "flow":
        agg = x.groupby([*group_cols, "quarter"], as_index=False)[value_col].sum()
    elif var_type == "index":
        agg = x.groupby([*group_cols, "quarter"], as_index=False)[value_col].mean()
    else:  # eop
        x = x.sort_values([*group_cols, date_col])
        agg = x.groupby([*group_cols, "quarter"], as_index=False).tail(1)
        agg = agg[[*group_cols, "quarter", value_col]]
    return agg


def annual_to_quarterly_proportional(
    annual_df: pd.DataFrame,
    indicator_q_df: pd.DataFrame,
    group_col: str,
    year_col: str,
    annual_value_col: str,
    indicator_value_col: str,
) -> pd.DataFrame:
    """
    A->Q distribution under annual benchmark constraint using quarterly indicators.
    This is a transparent baseline; can be replaced with Chow-Lin implementation.
    """
    a = annual_df.copy()
    i = indicator_q_df.copy()
    i["year"] = i["quarter"].dt.year

    s = i.groupby([group_col, "year"], as_index=False)[indicator_value_col].sum().rename(
        columns={indicator_value_col: "indicator_annual"}
    )
    i = i.merge(s, on=[group_col, "year"], how="left")

    m = i.merge(
        a[[group_col, year_col, annual_value_col]].rename(columns={year_col: "year"}),
        on=[group_col, "year"],
        how="left",
    )

    share = m[indicator_value_col] / m["indicator_annual"].replace(0, np.nan)
    m[annual_value_col.replace("_annual", "_q")] = m[annual_value_col] * share
    return m[[group_col, "quarter", annual_value_col.replace("_annual", "_q")]]


def align_macro_panel(df_macro_q: pd.DataFrame, axis: pd.DataFrame) -> pd.DataFrame:
    x = df_macro_q.copy()
    x["iso3"] = x["iso3"].astype(str).str.upper()
    x["quarter"] = pd.to_datetime(x["date_quarterly"]).dt.to_period("Q")

    x = x[x["iso3"].isin(COUNTRIES)]
    x = x[(x["quarter"] >= pd.Period(START)) & (x["quarter"] <= pd.Period(END))]

    # one row per (iso3, quarter)
    x = x.sort_values(["iso3", "quarter"]).drop_duplicates(["iso3", "quarter"], keep="last")

    skel = pd.MultiIndex.from_product([COUNTRIES, axis["quarter"]], names=["iso3", "quarter"]).to_frame(index=False)
    out = skel.merge(x, on=["iso3", "quarter"], how="left")
    out["year"] = out["quarter"].dt.year
    out["quarter_num"] = out["quarter"].dt.quarter
    out["date_quarterly"] = out["quarter"].dt.end_time

    cols = ["iso3", "quarter", "date_quarterly", "year", "quarter_num"] + [c for c in out.columns if c not in {"iso3", "quarter", "date_quarterly", "year", "quarter_num"}]
    return out[cols]


def align_bilateral_panel(df_bilat_q: pd.DataFrame, axis: pd.DataFrame) -> pd.DataFrame:
    x = df_bilat_q.copy()
    x["reporter_iso"] = x["reporter_iso"].astype(str).str.upper()
    x["partner_iso"] = x["partner_iso"].astype(str).str.upper()
    x["quarter"] = pd.to_datetime(x["date_quarterly"]).dt.to_period("Q")

    x = x[x["reporter_iso"].isin(COUNTRIES) & x["partner_iso"].isin(COUNTRIES)]
    x = x[(x["quarter"] >= pd.Period(START)) & (x["quarter"] <= pd.Period(END))]

    # aggregate duplicates across product/hs layers to country-pair-quarter
    keys = ["reporter_iso", "partner_iso", "quarter"]
    num_cols = x.select_dtypes(include=[np.number]).columns.tolist()
    num_cols = [c for c in num_cols if c not in ["year", "quarter"]]
    x = x.groupby(keys, as_index=False)[num_cols].sum(min_count=1)

    skel = pd.MultiIndex.from_product(
        [COUNTRIES, COUNTRIES, axis["quarter"]], names=["reporter_iso", "partner_iso", "quarter"]
    ).to_frame(index=False)
    out = skel.merge(x, on=keys, how="left")
    out["year"] = out["quarter"].dt.year
    out["quarter_num"] = out["quarter"].dt.quarter
    out["date_quarterly"] = out["quarter"].dt.end_time

    cols = ["reporter_iso", "partner_iso", "quarter", "date_quarterly", "year", "quarter_num"] + [c for c in out.columns if c not in {"reporter_iso", "partner_iso", "quarter", "date_quarterly", "year", "quarter_num"}]
    return out[cols]


def build_missing_matrix(df: pd.DataFrame, id_cols: list[str], target_cols: list[str]) -> pd.DataFrame:
    tmp = df[id_cols + target_cols].copy()
    miss = tmp[target_cols].isna().groupby([tmp[c] for c in id_cols]).sum()
    miss = miss.reset_index()
    return miss


def build_validation_report(axis: pd.DataFrame, macro: pd.DataFrame, bilat: pd.DataFrame) -> pd.DataFrame:
    n_q = len(axis)
    macro_cov = macro.groupby("iso3")["quarter"].nunique().reset_index(name="n_quarters_macro")
    macro_cov["macro_complete_96q"] = macro_cov["n_quarters_macro"] == n_q

    bilat_cov = bilat.groupby(["reporter_iso", "partner_iso"])["quarter"].nunique().reset_index(name="n_quarters_bilateral")
    bilat_cov["bilateral_complete_96q"] = bilat_cov["n_quarters_bilateral"] == n_q

    country_report = macro_cov.rename(columns={"iso3": "unit"})
    pair_report = bilat_cov.assign(unit=lambda d: d["reporter_iso"] + "->" + d["partner_iso"])

    out_country = country_report[["unit", "n_quarters_macro", "macro_complete_96q"]].copy()
    out_pair = pair_report[["unit", "n_quarters_bilateral", "bilateral_complete_96q"]].copy()

    out_country.columns = ["unit", "n_quarters", "is_complete"]
    out_pair.columns = ["unit", "n_quarters", "is_complete"]

    out_country.loc[:, "panel"] = "macro_country"
    out_pair.loc[:, "panel"] = "bilateral_pair"
    return pd.concat([out_country, out_pair], ignore_index=True)


def breakpoint_template() -> pd.DataFrame:
    rows = []
    for c in COUNTRIES:
        rows.append(
            {
                "iso3": c,
                "variable": "",
                "break_quarter": "",
                "break_type": "rebase/method_change/fiscal_year",
                "treatment": "splice_or_dummy",
                "notes": "",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    axis = build_master_quarter_axis(START, END)
    axis.to_csv(OUT_DIR / "quarter_master_index.csv", index=False)

    macro = pd.read_csv(MACRO_IN)
    bilat = pd.read_csv(BILAT_IN)

    macro_aligned = align_macro_panel(macro, axis)
    bilat_aligned = align_bilateral_panel(bilat, axis)

    macro_aligned.to_csv(OUT_DIR / "rcep_macro_aligned_2000Q1_2023Q4.csv", index=False)
    bilat_aligned.to_csv(OUT_DIR / "rcep_bilateral_aligned_2000Q1_2023Q4.csv", index=False)

    macro_targets = [c for c in macro_aligned.columns if c not in ["iso3", "quarter", "date_quarterly", "year", "quarter_num"]]
    bilat_targets = [c for c in bilat_aligned.columns if c not in ["reporter_iso", "partner_iso", "quarter", "date_quarterly", "year", "quarter_num"]]

    macro_missing = build_missing_matrix(macro_aligned, ["iso3"], macro_targets)
    bilat_missing = build_missing_matrix(bilat_aligned, ["reporter_iso", "partner_iso"], bilat_targets)

    macro_missing.to_csv(OUT_DIR / "macro_missing_matrix.csv", index=False)
    bilat_missing.to_csv(OUT_DIR / "bilateral_missing_matrix.csv", index=False)

    v_report = build_validation_report(axis, macro_aligned, bilat_aligned)
    v_report.to_csv(OUT_DIR / "alignment_validation_report.csv", index=False)

    bp = breakpoint_template()
    bp.to_csv(OUT_DIR / "breakpoint_log_template.csv", index=False)

    logger.info("Alignment complete. Outputs in %s", OUT_DIR)
    logger.info("Macro aligned rows=%s, Bilateral aligned rows=%s", len(macro_aligned), len(bilat_aligned))


if __name__ == "__main__":
    main()
