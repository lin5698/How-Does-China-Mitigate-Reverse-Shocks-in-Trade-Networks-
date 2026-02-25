import logging
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "research_output"
OUT_DIR = DATA_DIR / "nature_figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 7,
        "axes.titlesize": 8,
        "axes.labelsize": 7,
        "xtick.labelsize": 6,
        "ytick.labelsize": 6,
        "legend.fontsize": 6,
        "lines.linewidth": 1.0,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 300,
        "pdf.fonttype": 42,
    }
)


def _quarter_index(dt_series: pd.Series) -> pd.Series:
    return dt_series.dt.year * 4 + dt_series.dt.quarter


def _fit_panel_tc(df: pd.DataFrame):
    mod = PanelOLS.from_formula("A ~ TC_relief + EntityEffects + TimeEffects", data=df.set_index(["pair", "date"]))
    return mod.fit(cov_type="clustered", cluster_entity=True)


def make_fixed_weight_stability_table():
    in_path = DATA_DIR / "pairwise_regression_data_full.csv"
    if not in_path.exists():
        logger.warning("Missing %s; skip fixed-weight stability table.", in_path)
        return
    df = pd.read_csv(in_path)
    df["date"] = pd.to_datetime(df["date"])
    df["A"] = pd.to_numeric(df["A"], errors="coerce").clip(0, 1)
    df["TC_relief"] = pd.to_numeric(df.get("TC_relief", df["TC"].abs() * 100), errors="coerce")
    df["pair"] = df["reporter_iso"] + "_" + df["partner_iso"]
    df = df.dropna(subset=["A", "TC_relief", "pair", "date"])

    rows = []
    for w_type, label in [("Time-Varying", "Baseline (W_t)"), ("Fixed-Pre", "Fixed Weight (W_pre)")]:
        sub = df[(df["H"] == 8) & (df["W_type"] == w_type)].copy()
        if sub.empty:
            continue
        res = _fit_panel_tc(sub)
        rows.append(
            {
                "Specification": label,
                "beta_TC_relief": float(res.params["TC_relief"]),
                "se": float(res.std_errors["TC_relief"]),
                "t_stat": float(res.tstats["TC_relief"]),
                "p_value": float(res.pvalues["TC_relief"]),
                "N": int(res.nobs),
                "R_squared": float(res.rsquared),
            }
        )
    out = pd.DataFrame(rows)
    if len(out) == 2:
        b0 = out.loc[out["Specification"] == "Baseline (W_t)", "beta_TC_relief"].iloc[0]
        b1 = out.loc[out["Specification"] == "Fixed Weight (W_pre)", "beta_TC_relief"].iloc[0]
        out["coef_diff_vs_baseline"] = np.where(
            out["Specification"] == "Fixed Weight (W_pre)",
            b1 - b0,
            0.0,
        )
        out["coef_ratio_vs_baseline"] = np.where(
            out["Specification"] == "Fixed Weight (W_pre)",
            b1 / b0 if abs(b0) > 1e-12 else np.nan,
            1.0,
        )
    out.to_csv(OUT_DIR / "Table_Baseline_FixedWeight_Stability.csv", index=False)
    logger.info("Saved %s", OUT_DIR / "Table_Baseline_FixedWeight_Stability.csv")


def _rss_segment(y: np.ndarray, i: int, j: int) -> float:
    seg = y[i:j]
    if len(seg) == 0:
        return 0.0
    mu = seg.mean()
    return float(np.sum((seg - mu) ** 2))


def _best_breaks_dp(y: np.ndarray, max_breaks: int = 3, min_size: int = 8):
    n = len(y)
    max_seg = max_breaks + 1
    inf = 1e30
    dp = np.full((max_seg + 1, n + 1), inf)
    prev = np.full((max_seg + 1, n + 1), -1, dtype=int)
    dp[0, 0] = 0.0

    for s in range(1, max_seg + 1):
        for t in range(s * min_size, n + 1):
            lo = (s - 1) * min_size
            hi = t - min_size
            for k in range(lo, hi + 1):
                val = dp[s - 1, k] + _rss_segment(y, k, t)
                if val < dp[s, t]:
                    dp[s, t] = val
                    prev[s, t] = k

    candidates = []
    for s in range(1, max_seg + 1):
        rss = dp[s, n]
        if not np.isfinite(rss):
            continue
        p = s
        bic = n * np.log(max(rss / max(n, 1), 1e-12)) + p * np.log(max(n, 2))
        candidates.append((s - 1, bic, rss))
    if not candidates:
        return [], np.nan, np.nan
    k_best, bic_best, rss_best = min(candidates, key=lambda x: x[1])

    s = k_best + 1
    t = n
    cuts = []
    while s > 0:
        k = prev[s, t]
        if k <= 0:
            break
        cuts.append(k)
        t = k
        s -= 1
    cuts = sorted(cuts)
    return cuts, bic_best, rss_best


def _chow_f_stat(y: np.ndarray, cut: int) -> float:
    n = len(y)
    if cut <= 2 or cut >= n - 2:
        return np.nan
    rss_pooled = _rss_segment(y, 0, n)
    rss_split = _rss_segment(y, 0, cut) + _rss_segment(y, cut, n)
    k = 1
    denom_df = n - 2 * k
    if denom_df <= 0:
        return np.nan
    num = (rss_pooled - rss_split) / k
    den = rss_split / denom_df if rss_split > 0 else np.nan
    return float(num / den) if den and den > 0 else np.nan


def make_structural_break_table():
    agg_path = DATA_DIR / "rolling_resilience_metrics.csv"
    pair_path = DATA_DIR / "pairwise_rolling_metrics.csv"
    if not agg_path.exists() or not pair_path.exists():
        logger.warning("Missing rolling metrics files; skip break test table.")
        return

    agg = pd.read_csv(agg_path)
    agg["date"] = pd.to_datetime(agg["date"])
    pair = pd.read_csv(pair_path)
    pair["date"] = pd.to_datetime(pair["date"])

    series_map = {"Agg_A_t(H=8)": agg.set_index("date")["A_equal"].dropna()}
    for rep, par in [("CHN", "JPN"), ("CHN", "KOR"), ("CHN", "AUS")]:
        s = pair[(pair["reporter_iso"] == rep) & (pair["partner_iso"] == par)].set_index("date")["A"].dropna()
        if len(s) >= 20:
            series_map[f"Pair_{rep}<-{par}_A"] = s

    rows = []
    for name, s in series_map.items():
        y = s.values.astype(float)
        dates = s.index.to_list()
        cuts, bic, rss = _best_breaks_dp(y, max_breaks=3, min_size=8)
        f_stats = [_chow_f_stat(y, c) for c in cuts]
        break_dates = [dates[c].strftime("%YQ") for c in cuts]
        ci_l = [dates[max(c - 1, 0)].strftime("%YQ") for c in cuts]
        ci_u = [dates[min(c + 1, len(dates) - 1)].strftime("%YQ") for c in cuts]
        rows.append(
            {
                "Series": name,
                "num_breaks_selected": len(cuts),
                "break_dates": "; ".join(break_dates) if break_dates else "None",
                "break_CI_approx": "; ".join([f"[{l},{u}]" for l, u in zip(ci_l, ci_u)]) if cuts else "None",
                "max_Chow_F": np.nanmax(f_stats) if len(f_stats) else np.nan,
                "BIC": bic,
                "RSS": rss,
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "Table_Structural_Break_Tests.csv", index=False)
    logger.info("Saved %s", OUT_DIR / "Table_Structural_Break_Tests.csv")


def make_event_study_figure():
    in_path = DATA_DIR / "pairwise_regression_data_full.csv"
    if not in_path.exists():
        logger.warning("Missing %s; skip event-study figure.", in_path)
        return
    df = pd.read_csv(in_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["H"] == 8) & (df["W_type"] == "Time-Varying")].copy()
    df["A"] = pd.to_numeric(df["A"], errors="coerce").clip(0, 1)
    df["TC_relief"] = pd.to_numeric(df.get("TC_relief", df["TC"].abs() * 100), errors="coerce")
    df["pair"] = df["reporter_iso"] + "_" + df["partner_iso"]
    df = df.dropna(subset=["A", "TC_relief", "pair", "date"])

    # Use pair-specific "first major step-down" to avoid complete collinearity with time FE.
    pos = df[df["TC_relief"] > 0.1].copy()
    if pos.empty:
        logger.warning("No nontrivial TC relief for event-study.")
        return
    pair_max = pos.groupby("pair")["TC_relief"].max().rename("pair_tc_max")
    pos = pos.merge(pair_max, on="pair", how="left")
    pos = pos[pos["TC_relief"] >= 0.5 * pos["pair_tc_max"]]
    first_evt = (
        pos.sort_values("date")
        .groupby("pair", as_index=False)
        .first()[["pair", "date"]]
        .rename(columns={"date": "event_date"})
    )
    df = df.merge(first_evt, on="pair", how="inner")
    df["evt_k"] = _quarter_index(df["date"]) - _quarter_index(df["event_date"])
    df = df[(df["evt_k"] >= -8) & (df["evt_k"] <= 8)].copy()
    if df.empty:
        logger.warning("Event-study sample empty.")
        return

    ks = [k for k in range(-8, 9) if k != -1]
    term_map = {}
    for k in ks:
        nm = f"Dm{abs(k)}" if k < 0 else f"Dp{k}"
        df[nm] = (df["evt_k"] == k).astype(int)
        term_map[k] = nm
    rhs = " + ".join([term_map[k] for k in ks])
    model = PanelOLS.from_formula(
        f"A ~ {rhs} + EntityEffects + TimeEffects",
        data=df.set_index(["pair", "date"]),
        drop_absorbed=True,
    )
    res = model.fit(cov_type="clustered", cluster_entity=True)

    coefs, se = [], []
    for k in range(-8, 9):
        if k == -1:
            coefs.append(0.0)
            se.append(0.0)
        else:
            coefs.append(float(res.params.get(term_map[k], np.nan)))
            se.append(float(res.std_errors.get(term_map[k], np.nan)))
    coefs = np.array(coefs)
    se = np.array(se)
    x = np.arange(-8, 9)

    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axhline(0, color="black", linewidth=0.8, linestyle=":")
    ax.axvline(0, color="black", linewidth=0.8, linestyle="--")
    ax.fill_between(x, coefs - 1.96 * se, coefs + 1.96 * se, color="#56B4E9", alpha=0.25, label="95% CI")
    ax.fill_between(x, coefs - 1.0 * se, coefs + 1.0 * se, color="#56B4E9", alpha=0.45, label="68% CI")
    ax.plot(x, coefs, color="#0072B2", marker="o", markersize=3, label="Estimate")
    ax.set_xlabel("Event Time (quarters)")
    ax.set_ylabel("Effect on A")
    ax.set_title("Event Study Around Tariff Phase-ins (pair + time FE)", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "Fig_Event_Study_LeadsLags.pdf")
    plt.savefig(OUT_DIR / "Fig_Event_Study_LeadsLags.png", dpi=300)
    plt.close()
    logger.info("Saved %s", OUT_DIR / "Fig_Event_Study_LeadsLags.pdf")


def _net_pos(df: pd.DataFrame, value_col: str, period_col: str = "period") -> pd.DataFrame:
    out = df.groupby([period_col, "partner_iso"])[value_col].mean().unstack(period_col)
    inc = df.groupby([period_col, "reporter_iso"])[value_col].mean().unstack(period_col)
    out = out.rename_axis(index="iso3")
    inc = inc.rename_axis(index="iso3")
    pos = out.sub(inc, fill_value=np.nan)
    return pos


def _plot_rank_slope(ax, pos_df: pd.DataFrame, title: str):
    pos_df = pos_df.dropna(subset=["Pre", "Post"]).copy()
    if pos_df.empty:
        return
    rank_pre = pos_df["Pre"].rank(ascending=True, method="average")
    rank_post = pos_df["Post"].rank(ascending=True, method="average")
    pos_df = pos_df.assign(rank_pre=rank_pre, rank_post=rank_post).sort_values("rank_post")

    for iso, r in pos_df.iterrows():
        color = "#009E73" if r["rank_post"] > r["rank_pre"] else ("#D55E00" if r["rank_post"] < r["rank_pre"] else "#999999")
        ax.plot([0, 1], [r["rank_pre"], r["rank_post"]], color=color, linewidth=1.0, marker="o", markersize=2.8, alpha=0.85)
        ax.text(-0.04, r["rank_pre"], iso, ha="right", va="center", fontsize=5.5)
        ax.text(1.04, r["rank_post"], iso, ha="left", va="center", fontsize=5.5)
    ax.set_xlim(-0.35, 1.35)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Pre\n(2016-2019)", "Impl.\n(2022-2024)"])
    ax.invert_yaxis()
    ax.set_ylabel("Absorber Rank (lower = more spillover)")
    ax.set_title(title, loc="left", fontweight="bold")
    ax.yaxis.grid(True, linestyle="--", alpha=0.25)


def make_alt_absorber_measure_figure():
    p = DATA_DIR / "pairwise_rolling_metrics.csv"
    if not p.exists():
        logger.warning("Missing %s; skip alternative absorber-position figure.", p)
        return
    df = pd.read_csv(p)
    df["date"] = pd.to_datetime(df["date"])
    df["period"] = np.where(df["date"] < pd.Timestamp("2020-01-01"), "Pre", np.where(df["date"] >= pd.Timestamp("2022-01-01"), "Post", "Other"))
    df = df[df["period"].isin(["Pre", "Post"])].copy()
    if df.empty:
        logger.warning("No pre/post observations for absorber comparison.")
        return

    pos_a = _net_pos(df, "A")
    pos_s = _net_pos(df, "S_total")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 4.2), sharey=True)
    _plot_rank_slope(axes[0], pos_a, "a. Amplification-share-based")
    _plot_rank_slope(axes[1], pos_s, "b. Cumulative-response-based")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "Fig_Alternative_Absorber_Position_Measures.pdf")
    plt.savefig(OUT_DIR / "Fig_Alternative_Absorber_Position_Measures.png", dpi=300)
    plt.close()
    logger.info("Saved %s", OUT_DIR / "Fig_Alternative_Absorber_Position_Measures.pdf")


def main():
    make_fixed_weight_stability_table()
    make_structural_break_table()
    make_event_study_figure()
    make_alt_absorber_measure_figure()
    logger.info("Additional requested outputs complete.")


if __name__ == "__main__":
    main()
