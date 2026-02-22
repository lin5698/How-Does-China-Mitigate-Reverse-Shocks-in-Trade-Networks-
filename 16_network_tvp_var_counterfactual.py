"""
Network-TVP-VAR style quarterly framework for RCEP reverse-shock resilience.

This script implements an operational, data-driven approximation of the model
used in the paper draft:
1) Quarterly VAX construction with annual benchmarking and high-frequency indicators.
2) Time-varying network construction W_t (smoothed trade-share matrix).
3) Country-level rolling estimation of dynamic coefficients (own lag + network lag + global PCs).
4) Low-rank compression of time-varying network coefficients.
5) Counterfactual decomposition (total vs direct) based on GIRF-style impulse mapping.
6) Rolling out-of-sample evaluation (h=1,4) against AR(1) and no-network benchmarks.

Outputs are written to data/model_outputs/.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from config import RCEP_COUNTRIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent
MACRO_FILE = ROOT / "master_quarterly_macro_2005_2024.csv"
BILAT_FILE = ROOT / "master_quarterly_bilateral_2005_2024.csv"
OUT_DIR = ROOT / "data" / "model_outputs"

COUNTRIES = list(RCEP_COUNTRIES.keys())
EPS = 1e-9


@dataclass
class ModelConfig:
    start_year: int = 2010
    end_year: int = 2023
    window: int = 24  # quarters
    pca_k: int = 2
    ridge_alpha: float = 1.0
    network_smoothing_m: int = 4
    rank_r: int = 3
    irf_h: int = 8


def load_and_filter_data(cfg: ModelConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    macro = pd.read_csv(MACRO_FILE)
    bilat = pd.read_csv(BILAT_FILE)

    macro["date"] = pd.to_datetime(macro["date_quarterly"])
    bilat["date"] = pd.to_datetime(bilat["date_quarterly"])

    macro = macro[
        (macro["iso3"].isin(COUNTRIES))
        & (macro["date"].dt.year >= cfg.start_year)
        & (macro["date"].dt.year <= cfg.end_year)
    ].copy()

    bilat = bilat[
        (bilat["reporter_iso"].isin(COUNTRIES))
        & (bilat["partner_iso"].isin(COUNTRIES))
        & (bilat["date"].dt.year >= cfg.start_year)
        & (bilat["date"].dt.year <= cfg.end_year)
    ].copy()

    logger.info("Macro rows: %s, Bilateral rows: %s", len(macro), len(bilat))
    return macro, bilat


def construct_quarterly_vax(macro: pd.DataFrame) -> pd.DataFrame:
    """
    Construct a quarterly VAX proxy with annual consistency:
    - Build indicator from exports and industrial activity proxy (GDP-VOL).
    - Build annual benchmark from implied value-added share times annual exports.
    - Allocate annual benchmark to quarters proportional to indicator.
    """
    df = macro.copy()
    df = df.sort_values(["iso3", "date"])

    # Indicator components
    exp_q = df["total_exports_usd_k"].fillna(0.0)
    ind_q = df["GDP-VOL"].ffill().bfill()
    ind_q = ind_q.replace(0, np.nan).fillna(ind_q.median())
    indicator = np.maximum(exp_q, 0) * np.maximum(ind_q, 0)
    df["vax_indicator_q"] = np.where(indicator <= 0, EPS, indicator)

    # Annual benchmark: export value * value-added ratio proxy
    va_ratio = (df["GDP-VOL"] / (df["gdp_current_usd"] + EPS)).clip(lower=0.1, upper=1.0)
    va_ratio = va_ratio.fillna(0.5)
    df["vax_proxy_q_pre"] = exp_q * va_ratio

    df["year"] = df["date"].dt.year
    annual = (
        df.groupby(["iso3", "year"], as_index=False)
        .agg(vax_annual=("vax_proxy_q_pre", "sum"), ind_annual=("vax_indicator_q", "sum"))
    )
    df = df.merge(annual, on=["iso3", "year"], how="left")

    # Benchmarking allocation
    share = df["vax_indicator_q"] / (df["ind_annual"] + EPS)
    df["vax_q"] = df["vax_annual"] * share
    df["vax_q"] = df["vax_q"].clip(lower=EPS)

    df["ln_vax"] = np.log(df["vax_q"])
    df["vax_growth_qoq"] = df.groupby("iso3")["ln_vax"].diff()
    df["vax_growth_yoy"] = df.groupby("iso3")["ln_vax"].diff(4)
    return df


def build_smoothed_network_matrices(
    bilat: pd.DataFrame, dates: List[pd.Timestamp], m: int
) -> Dict[pd.Timestamp, np.ndarray]:
    matrices: Dict[pd.Timestamp, np.ndarray] = {}
    cidx = {c: i for i, c in enumerate(COUNTRIES)}

    for d in dates:
        window_dates = [x for x in dates if (x <= d and x >= d - pd.offsets.QuarterEnd(m - 1))]
        sub = bilat[bilat["date"].isin(window_dates)]

        raw = np.zeros((len(COUNTRIES), len(COUNTRIES)))
        if not sub.empty:
            grouped = sub.groupby(["reporter_iso", "partner_iso"])["export_usd"].sum().reset_index()
            for _, row in grouped.iterrows():
                i = cidx[row["reporter_iso"]]
                j = cidx[row["partner_iso"]]
                raw[i, j] = max(row["export_usd"], 0.0)

        np.fill_diagonal(raw, 0.0)
        row_sum = raw.sum(axis=1, keepdims=True)
        w = np.divide(raw, row_sum, out=np.zeros_like(raw), where=row_sum > 0)
        matrices[d] = w

    return matrices


def construct_pca_factors(df_vax: pd.DataFrame, k: int) -> pd.DataFrame:
    piv = df_vax.pivot_table(index="date", columns="iso3", values="vax_growth_qoq")
    piv = piv.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    z = (piv - piv.mean()) / (piv.std(ddof=0) + EPS)
    z = z.fillna(0.0)

    x = z.values
    cov = np.cov(x, rowvar=False)
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvals = eigvals[order]
    eigvecs = eigvecs[:, order]
    kk = min(k, eigvecs.shape[1])
    loadings = eigvecs[:, :kk]
    fac = x @ loadings

    fac_df = pd.DataFrame(fac, index=z.index, columns=[f"pc{i+1}" for i in range(fac.shape[1])]).reset_index()
    exp_var = eigvals[:kk] / (eigvals.sum() + EPS)
    logger.info("PCA explained variance: %s", np.round(exp_var, 4))
    return fac_df


def rolling_country_coefficients(
    df_vax: pd.DataFrame,
    W_map: Dict[pd.Timestamp, np.ndarray],
    fac_df: pd.DataFrame,
    cfg: ModelConfig,
) -> pd.DataFrame:
    panel = df_vax[["date", "iso3", "vax_growth_qoq"]].copy()

    records = []
    dates = sorted(panel["date"].unique())

    for d in dates:
        W = W_map[d]
        g = panel[panel["date"] == d].set_index("iso3")["vax_growth_qoq"].reindex(COUNTRIES).fillna(0.0).values
        wg = W @ g
        for i, c in enumerate(COUNTRIES):
            records.append({"date": d, "iso3": c, "y": g[i], "Wy": wg[i]})

    reg = pd.DataFrame(records).sort_values(["iso3", "date"])
    reg["y_l1"] = reg.groupby("iso3")["y"].shift(1)
    reg["Wy_l1"] = reg.groupby("iso3")["Wy"].shift(1)
    reg = reg.merge(fac_df, on="date", how="left").fillna(0.0)

    pc_cols = [c for c in reg.columns if c.startswith("pc")]

    out = []
    for c in COUNTRIES:
        sub = reg[reg["iso3"] == c].dropna(subset=["y_l1", "Wy_l1"]).reset_index(drop=True)
        if len(sub) <= cfg.window + 4:
            continue

        for t in range(cfg.window, len(sub)):
            win = sub.iloc[t - cfg.window : t]
            x_cols = ["y_l1", "Wy_l1"] + pc_cols
            X = win[x_cols].values
            y = win["y"].values

            X_aug = np.column_stack([np.ones(len(X)), X])
            I = np.eye(X_aug.shape[1])
            I[0, 0] = 0.0  # do not penalize intercept
            beta = np.linalg.solve(X_aug.T @ X_aug + cfg.ridge_alpha * I, X_aug.T @ y)

            x_next = np.concatenate([[1.0], sub.iloc[t][x_cols].values])
            pred = float(x_next @ beta)
            resid = float(sub.iloc[t]["y"] - pred)
            train_resid = y - (X_aug @ beta)

            out.append(
                {
                    "date": sub.iloc[t]["date"],
                    "iso3": c,
                    "alpha": float(beta[0]),
                    "a_own": float(beta[1]),
                    "b_net": float(beta[2]),
                    "sigma": float(np.std(train_resid)),
                    "y_true": float(sub.iloc[t]["y"]),
                    "y_pred": pred,
                    "resid": resid,
                }
            )

    return pd.DataFrame(out)


def low_rank_compress_network(coeff_df: pd.DataFrame, rank_r: int) -> Tuple[pd.DataFrame, np.ndarray]:
    dates = sorted(coeff_df["date"].unique())
    tensor = np.zeros((len(dates), len(COUNTRIES), len(COUNTRIES)))

    for t_idx, d in enumerate(dates):
        sub = coeff_df[coeff_df["date"] == d].set_index("iso3")
        b = sub["b_net"].reindex(COUNTRIES).fillna(0.0).values
        # country-specific network loading on row; interaction via partner exposure
        tensor[t_idx] = np.diag(b)

    unfold = tensor.reshape(len(dates), -1)
    U, S, Vt = np.linalg.svd(unfold, full_matrices=False)
    r = min(rank_r, len(S))
    recon = (U[:, :r] * S[:r]) @ Vt[:r, :]
    recon_tensor = recon.reshape(tensor.shape)

    # write back smoothed low-rank b_net
    rows = []
    for t_idx, d in enumerate(dates):
        diag_b = np.diag(recon_tensor[t_idx])
        for i, c in enumerate(COUNTRIES):
            rows.append({"date": d, "iso3": c, "b_net_cp": diag_b[i]})

    cp_df = pd.DataFrame(rows)
    return cp_df, S


def generalized_irf(phi: np.ndarray, sigma: np.ndarray, origin_j: int, H: int) -> np.ndarray:
    n = phi.shape[0]
    e_j = np.zeros((n, 1))
    e_j[origin_j, 0] = 1.0

    den = float(np.sqrt((e_j.T @ sigma @ e_j).item()) + EPS)
    out = np.zeros((n, H + 1))

    phi_h = np.eye(n)
    for h in range(H + 1):
        out[:, h] = ((phi_h @ sigma @ e_j) / den).ravel()
        phi_h = phi_h @ phi

    return out


def counterfactual_decomposition(
    coeff_df: pd.DataFrame,
    cp_df: pd.DataFrame,
    W_map: Dict[pd.Timestamp, np.ndarray],
    H: int,
) -> pd.DataFrame:
    merged = coeff_df.merge(cp_df, on=["date", "iso3"], how="left")
    dates = sorted(merged["date"].unique())

    recs = []
    for d in dates:
        sub = merged[merged["date"] == d].set_index("iso3").reindex(COUNTRIES)
        a = sub["a_own"].fillna(0.0).values
        b = sub["b_net_cp"].fillna(0.0).values
        sig = np.diag(np.square(sub["sigma"].fillna(sub["sigma"].median()).values + EPS))

        W = W_map.get(d, np.zeros((len(COUNTRIES), len(COUNTRIES))))
        phi_total = np.diag(a) + np.diag(b) @ W
        phi_direct = np.diag(a)

        for j, origin in enumerate(COUNTRIES):
            irf_total = generalized_irf(phi_total, sig, j, H)
            irf_direct = generalized_irf(phi_direct, sig, j, H)

            for i, target in enumerate(COUNTRIES):
                st = np.sum(np.abs(irf_total[i, :]))
                sd = np.sum(np.abs(irf_direct[i, :]))
                amp = (st - sd) / (st + EPS)
                recs.append(
                    {
                        "date": d,
                        "target": target,
                        "origin": origin,
                        "S_total": st,
                        "S_direct": sd,
                        "A_share": float(np.clip(amp, 0.0, 1.0)),
                    }
                )

    res = pd.DataFrame(recs)

    # absorber position: high means absorbs more than amplifies
    pos = (
        res.groupby(["date", "target"]) ["A_share"].mean().reset_index().rename(columns={"target": "iso3", "A_share": "inbound_A"})
        .merge(
            res.groupby(["date", "origin"])["A_share"].mean().reset_index().rename(columns={"origin": "iso3", "A_share": "outbound_A"}),
            on=["date", "iso3"],
            how="left",
        )
    )
    pos["net_absorbing_position"] = pos["inbound_A"] - pos["outbound_A"]
    return res.merge(pos[["date", "iso3", "net_absorbing_position"]], left_on=["date", "target"], right_on=["date", "iso3"], how="left").drop(columns=["iso3"])


def forecast_evaluation(coeff_df: pd.DataFrame) -> pd.DataFrame:
    """Compute h=1 and h=4 performance against simple benchmarks."""
    df = coeff_df.sort_values(["iso3", "date"]).copy()
    rows = []
    for h in [1, 4]:
        for c in COUNTRIES:
            sub = df[df["iso3"] == c].reset_index(drop=True)
            if len(sub) <= h + 5:
                continue

            y_true = sub["y_true"].shift(-h).dropna().values
            y_model = sub["y_pred"].shift(-h).dropna().values
            y_ar1 = sub["y_true"].shift(1).shift(-h).dropna().values
            y_nonet = (sub["alpha"] + sub["a_own"] * sub["y_true"].shift(1)).shift(-h).dropna().values

            n = min(len(y_true), len(y_model), len(y_ar1), len(y_nonet))
            if n < 5:
                continue
            y_true, y_model, y_ar1, y_nonet = y_true[:n], y_model[:n], y_ar1[:n], y_nonet[:n]

            mse_model = float(np.mean((y_true - y_model) ** 2))
            mse_ar1 = float(np.mean((y_true - y_ar1) ** 2))
            mse_nonet = float(np.mean((y_true - y_nonet) ** 2))

            rows.append(
                {
                    "iso3": c,
                    "h": h,
                    "rmse_model": float(np.sqrt(mse_model)),
                    "mae_model": float(np.mean(np.abs(y_true - y_model))),
                    "rmse_ar1": float(np.sqrt(mse_ar1)),
                    "rmse_no_network": float(np.sqrt(mse_nonet)),
                    "r2_oos_vs_ar1": float(1.0 - mse_model / (mse_ar1 + EPS)),
                }
            )

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    summary = out.groupby("h", as_index=False).mean(numeric_only=True)
    return summary


def run_model(cfg: ModelConfig) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    macro, bilat = load_and_filter_data(cfg)
    vax = construct_quarterly_vax(macro)

    dates = sorted(vax["date"].unique())
    W_map = build_smoothed_network_matrices(bilat, dates, cfg.network_smoothing_m)
    factors = construct_pca_factors(vax, cfg.pca_k)

    coeff = rolling_country_coefficients(vax, W_map, factors, cfg)
    if coeff.empty:
        raise RuntimeError("No coefficients estimated. Check data coverage and window settings.")

    cp_df, singular_vals = low_rank_compress_network(coeff, cfg.rank_r)
    decomp = counterfactual_decomposition(coeff, cp_df, W_map, cfg.irf_h)
    eval_df = forecast_evaluation(coeff)

    coeff.to_csv(OUT_DIR / "tvp_country_coefficients.csv", index=False)
    cp_df.to_csv(OUT_DIR / "cp_compressed_network_coefficients.csv", index=False)
    decomp.to_csv(OUT_DIR / "counterfactual_amplification_panel.csv", index=False)
    eval_df.to_csv(OUT_DIR / "rolling_forecast_evaluation.csv", index=False)

    summary = {
        "sample_start": str(min(dates).date()),
        "sample_end": str(max(dates).date()),
        "n_countries": len(COUNTRIES),
        "n_quarters": len(dates),
        "avg_amplification_share": float(decomp["A_share"].mean()),
        "rank_singular_values": [float(x) for x in singular_vals[: cfg.rank_r]],
    }
    pd.Series(summary).to_json(OUT_DIR / "model_run_summary.json", force_ascii=False, indent=2)

    logger.info("Model outputs written to %s", OUT_DIR)
    if not eval_df.empty:
        logger.info("Forecast summary:\n%s", eval_df.to_string(index=False))


if __name__ == "__main__":
    run_model(ModelConfig())
