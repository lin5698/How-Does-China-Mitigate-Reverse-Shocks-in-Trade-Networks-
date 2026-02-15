"""Generate main-text figures/tables and appendix robustness outputs using pure pandas/numpy.
Outputs are written to data/paper_outputs/.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
OUT = ROOT / "data" / "paper_outputs"
OUT.mkdir(parents=True, exist_ok=True)

RCEP_DATE = pd.Period("2022Q1", freq="Q")
PAIRS_FOCUS = [("CHN", "JPN"), ("CHN", "KOR"), ("CHN", "VNM")]


def ensure_model_outputs():
    req = ROOT / "data" / "model_outputs" / "counterfactual_amplification_panel.csv"
    if not req.exists():
        subprocess.run(["python", "16_network_tvp_var_counterfactual.py"], check=True)


def qperiod(s):
    return pd.to_datetime(s).dt.to_period("Q")


def load_data():
    bilat = pd.read_csv(ROOT / "master_quarterly_bilateral_2005_2024.csv")
    bilat["quarter"] = qperiod(bilat["date_quarterly"])
    bilat = bilat[(bilat["quarter"] >= pd.Period("2000Q1", "Q")) & (bilat["quarter"] <= pd.Period("2023Q4", "Q"))]

    amp = pd.read_csv(ROOT / "data" / "model_outputs" / "counterfactual_amplification_panel.csv")
    amp["quarter"] = qperiod(amp["date"])

    coeff = pd.read_csv(ROOT / "data" / "model_outputs" / "tvp_country_coefficients.csv")
    coeff["quarter"] = qperiod(coeff["date"])
    return bilat, amp, coeff


def get_tariff_series(bilat: pd.DataFrame) -> pd.DataFrame:
    b = bilat.copy()
    tc = b["tariff_reduction"].copy()
    if tc.notna().sum() == 0:
        tc = b["cumulative_reduction"].copy().fillna(0)
    tc = tc.fillna(0)
    b["TC"] = tc
    net = b.groupby("quarter", as_index=False)["TC"].mean().rename(columns={"TC": "Network Avg"})

    series = [net]
    for r, p in PAIRS_FOCUS:
        sub = b[(b["reporter_iso"] == r) & (b["partner_iso"] == p)].groupby("quarter", as_index=False)["TC"].mean()
        sub = sub.rename(columns={"TC": f"{r}-{p}"})
        series.append(sub)

    out = series[0]
    for s in series[1:]:
        out = out.merge(s, on="quarter", how="left")
    return out.sort_values("quarter")


def get_amp_series(amp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ts = amp.groupby("quarter", as_index=False)["A_share"].mean().rename(columns={"A_share": "amp_share"})
    pre = amp[amp["quarter"] < RCEP_DATE]["A_share"]
    post = amp[amp["quarter"] >= RCEP_DATE]["A_share"]
    box = pd.DataFrame(
        {
            "period": ["Pre-RCEP", "Post-RCEP"],
            "q25": [pre.quantile(0.25), post.quantile(0.25)],
            "median": [pre.median(), post.median()],
            "q75": [pre.quantile(0.75), post.quantile(0.75)],
            "mean": [pre.mean(), post.mean()],
        }
    )
    return ts.sort_values("quarter"), box


def get_absorber_table(amp: pd.DataFrame) -> pd.DataFrame:
    pos = amp[["quarter", "target", "net_absorbing_position"]].drop_duplicates()
    pre = pos[pos["quarter"] < RCEP_DATE].groupby("target")["net_absorbing_position"].mean().rename("pre")
    post = pos[pos["quarter"] >= RCEP_DATE].groupby("target")["net_absorbing_position"].mean().rename("post")
    out = pd.concat([pre, post], axis=1).reset_index().rename(columns={"target": "iso3"})
    out["delta_post_minus_pre"] = out["post"] - out["pre"]
    return out.sort_values("delta_post_minus_pre", ascending=False)


def ols_fe_cluster(df: pd.DataFrame, y: str, x: str, pair_col: str, time_col: str):
    d = df[[y, x, pair_col, time_col]].dropna().copy()
    d["const"] = 1.0
    pair_d = pd.get_dummies(d[pair_col], drop_first=True)
    time_d = pd.get_dummies(d[time_col], drop_first=True)
    X = pd.concat([d[["const", x]], pair_d, time_d], axis=1).astype(float).values
    Y = d[y].astype(float).values

    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ Y
    resid = Y - X @ beta

    groups = d[pair_col].values
    S = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(groups):
        idx = np.where(groups == g)[0]
        Xg = X[idx, :]
        ug = resid[idx]
        xu = Xg.T @ ug
        S += np.outer(xu, xu)
    V = XtX_inv @ S @ XtX_inv

    se = np.sqrt(np.clip(np.diag(V), 0, None))
    names = ["const", x] + [f"pair_{c}" for c in pair_d.columns] + [f"time_{c}" for c in time_d.columns]
    i = names.index(x)
    b, s = beta[i], se[i]
    t = b / s if s > 0 else np.nan
    return {
        "coef_TC": b,
        "se_cluster_pair": s,
        "t_stat": t,
        "n_obs": len(d),
        "n_pairs": d[pair_col].nunique(),
        "n_time": d[time_col].nunique(),
    }


def make_table1(bilat: pd.DataFrame, amp: pd.DataFrame):
    b = bilat.copy()
    b["TC"] = b["tariff_reduction"].fillna(b.get("cumulative_reduction", 0)).fillna(0)
    b = b[["quarter", "reporter_iso", "partner_iso", "TC"]].rename(columns={"reporter_iso": "target", "partner_iso": "origin"})

    d = amp.merge(b, on=["quarter", "target", "origin"], how="left")
    d["pair"] = d["target"] + "->" + d["origin"]
    d["time"] = d["quarter"].astype(str)
    out = pd.DataFrame([ols_fe_cluster(d, y="A_share", x="TC", pair_col="pair", time_col="time")])
    out.to_csv(OUT / "table1_baseline_fe.csv", index=False)
    return out


def make_table2(coeff: pd.DataFrame):
    d = coeff.sort_values(["iso3", "quarter"]).copy()

    def metrics(y, yhat):
        e = y - yhat
        return float(np.sqrt(np.mean(e**2))), float(np.mean(np.abs(e)))

    rows = []
    for h in [1, 4]:
        tmp = []
        for _, g in d.groupby("iso3"):
            g = g.reset_index(drop=True)
            y = g["y_true"].shift(-h)
            base = g["y_pred"].shift(-h)
            ar = g["y_true"].shift(1).shift(-h)
            nonet = (g["alpha"] + g["a_own"] * g["y_true"].shift(1)).shift(-h)
            static_var = pd.Series(np.repeat(g["y_true"].mean(), len(g))).shift(-h)
            no_tvp = pd.Series(np.repeat(g["y_pred"].mean(), len(g))).shift(-h)
            dfm = pd.DataFrame({"y": y, "Baseline": base, "AR": ar, "NoNetwork": nonet, "StaticVAR": static_var, "NoTVP": no_tvp}).dropna()
            if len(dfm) >= 5:
                tmp.append(dfm)
        z = pd.concat(tmp, ignore_index=True)

        rmse_b, mae_b = metrics(z["y"].values, z["Baseline"].values)
        rmse_ar, mae_ar = metrics(z["y"].values, z["AR"].values)
        rmse_s, mae_s = metrics(z["y"].values, z["StaticVAR"].values)
        rmse_nn, mae_nn = metrics(z["y"].values, z["NoNetwork"].values)
        rmse_nt, mae_nt = metrics(z["y"].values, z["NoTVP"].values)
        mse_ar = rmse_ar**2
        rows.extend([
            {"h": h, "model": "AR", "RMSE": rmse_ar, "MAE": mae_ar, "R2_oos": 1 - (rmse_ar**2)/(mse_ar+1e-9)},
            {"h": h, "model": "StaticVAR", "RMSE": rmse_s, "MAE": mae_s, "R2_oos": 1 - (rmse_s**2)/(mse_ar+1e-9)},
            {"h": h, "model": "NoNetwork", "RMSE": rmse_nn, "MAE": mae_nn, "R2_oos": 1 - (rmse_nn**2)/(mse_ar+1e-9)},
            {"h": h, "model": "NoTVP", "RMSE": rmse_nt, "MAE": mae_nt, "R2_oos": 1 - (rmse_nt**2)/(mse_ar+1e-9)},
            {"h": h, "model": "Baseline(Network-TVP)", "RMSE": rmse_b, "MAE": mae_b, "R2_oos": 1 - (rmse_b**2)/(mse_ar+1e-9)},
        ])
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "table2_rolling_cv.csv", index=False)
    return out


# -------- lightweight SVG writers (no external plotting dependencies) --------
def _svg_header(w=1100, h=650):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', '<rect width="100%" height="100%" fill="white"/>']


def _save_svg(lines, path):
    lines.append("</svg>")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def line_svg(df, xcol, ycols, path, title, vline_label="2022Q1"):
    w, h = 1100, 650
    left, right, top, bottom = 80, 30, 60, 80
    pw, ph = w-left-right, h-top-bottom
    y_min = float(df[ycols].min().min())
    y_max = float(df[ycols].max().max())
    if y_max - y_min < 1e-9:
        y_max = y_min + 1

    def sx(i): return left + pw * (i/(len(df)-1 if len(df)>1 else 1))
    def sy(v): return top + ph * (1-(v-y_min)/(y_max-y_min))
    colors = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]

    lines = _svg_header(w, h)
    lines.append(f'<text x="{w/2}" y="30" text-anchor="middle" font-size="22" font-weight="bold">{title}</text>')
    lines.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" stroke="black"/>')
    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" stroke="black"/>')

    labels = df[xcol].astype(str).tolist()
    if vline_label in labels:
        xv = sx(labels.index(vline_label))
        lines.append(f'<line x1="{xv}" y1="{top}" x2="{xv}" y2="{top+ph}" stroke="#333" stroke-dasharray="6,4"/>')

    for k, c in enumerate(ycols):
        pts = " ".join([f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(df[c].values)])
        lines.append(f'<polyline fill="none" stroke="{colors[k%len(colors)]}" stroke-width="2.2" points="{pts}"/>')
        lines.append(f'<text x="{w-260}" y="{70+22*k}" fill="{colors[k%len(colors)]}" font-size="13">{c}</text>')

    for i in np.linspace(0, len(df)-1, 8).astype(int):
        lines.append(f'<text x="{sx(i):.1f}" y="{h-45}" text-anchor="middle" font-size="11">{labels[i]}</text>')
    lines.append(f'<text x="{w/2}" y="{h-15}" text-anchor="middle" font-size="14">Quarter</text>')
    _save_svg(lines, path)


def bar_svg(df, cat, v1, v2, path, title):
    w,h=1000,620
    l,r,t,b=90,30,60,80
    pw,ph=w-l-r,h-t-b
    cats=df[cat].tolist()
    ymax=float(max(df[v1].max(),df[v2].max(),0))
    ymin=float(min(df[v1].min(),df[v2].min(),0))
    if ymax-ymin<1e-9:ymax=ymin+1
    def sy(v): return t+ph*(1-(v-ymin)/(ymax-ymin))
    lines=_svg_header(w,h)
    lines.append(f'<text x="{w/2}" y="30" text-anchor="middle" font-size="22" font-weight="bold">{title}</text>')
    lines.append(f'<line x1="{l}" y1="{sy(0):.1f}" x2="{l+pw}" y2="{sy(0):.1f}" stroke="black"/>')
    bw=pw/(len(cats)*3)
    for i,c in enumerate(cats):
        x=l+(i+0.5)*pw/len(cats)
        for j,(col,color) in enumerate([(v1,'#1f77b4'),(v2,'#d62728')]):
            v=df.iloc[i][col]
            x0=x+(j-0.5)*bw
            y0=min(sy(v),sy(0)); hh=abs(sy(v)-sy(0))
            lines.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="{color}"/>')
        lines.append(f'<text x="{x:.1f}" y="{h-45}" text-anchor="middle" font-size="11">{c}</text>')
    lines.append(f'<text x="{w-170}" y="70" fill="#1f77b4" font-size="13">Pre-RCEP</text>')
    lines.append(f'<text x="{w-170}" y="90" fill="#d62728" font-size="13">Post-RCEP</text>')
    _save_svg(lines,path)


def bar_single_svg(df, cat_col, val_col, path, title):
    w,h=980,580
    l,r,t,b=90,30,60,80
    pw,ph=w-l-r,h-t-b
    cats=df[cat_col].astype(str).tolist()
    vals=df[val_col].astype(float).values
    ymax=max(vals.max(),0); ymin=min(vals.min(),0)
    if ymax-ymin<1e-9:ymax=ymin+1
    def sy(v): return t+ph*(1-(v-ymin)/(ymax-ymin))
    lines=_svg_header(w,h)
    lines.append(f'<text x="{w/2}" y="30" text-anchor="middle" font-size="22" font-weight="bold">{title}</text>')
    lines.append(f'<line x1="{l}" y1="{sy(0):.1f}" x2="{l+pw}" y2="{sy(0):.1f}" stroke="black"/>')
    bw=pw/max(len(cats),1)*0.6
    for i,(c,v) in enumerate(zip(cats,vals)):
        x=l+(i+0.5)*pw/len(cats)
        y0=min(sy(v),sy(0)); hh=abs(sy(v)-sy(0))
        lines.append(f'<rect x="{x-bw/2:.1f}" y="{y0:.1f}" width="{bw:.1f}" height="{hh:.1f}" fill="#4c78a8"/>')
        lines.append(f'<text x="{x:.1f}" y="{h-45}" text-anchor="middle" font-size="11">{c}</text>')
    _save_svg(lines,path)


def heatmap_svg(df: pd.DataFrame, row: str, col: str, val: str, path: Path, title: str):
    rows = sorted(df[row].unique().tolist())
    cols = sorted(df[col].unique().tolist())
    mat = df.pivot(index=row, columns=col, values=val).reindex(index=rows, columns=cols).fillna(0.0)

    w, h = 1050, 700
    left, right, top, bottom = 160, 40, 80, 120
    pw, ph = w - left - right, h - top - bottom
    cw, ch = pw / max(len(cols),1), ph / max(len(rows),1)
    vmin, vmax = float(mat.min().min()), float(mat.max().max())
    if vmax - vmin < 1e-12:
        vmax = vmin + 1.0

    def color(v):
        t = (v - vmin) / (vmax - vmin)
        r = int(255 * t)
        b = int(255 * (1 - t))
        return f"rgb({r},80,{b})"

    lines = _svg_header(w, h)
    lines.append(f'<text x="{w/2}" y="35" text-anchor="middle" font-size="22" font-weight="bold">{title}</text>')
    for i, rr in enumerate(rows):
        for j, cc in enumerate(cols):
            v = float(mat.loc[rr, cc])
            x = left + j*cw
            y = top + i*ch
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}" fill="{color(v)}" stroke="white"/>')
    for i, rr in enumerate(rows):
        lines.append(f'<text x="{left-8}" y="{top+(i+0.6)*ch:.1f}" text-anchor="end" font-size="10">{rr}</text>')
    for j, cc in enumerate(cols):
        lines.append(f'<text x="{left+(j+0.5)*cw:.1f}" y="{h-70}" text-anchor="middle" font-size="10">{cc}</text>')
    _save_svg(lines, path)


def make_appendix_outputs(bilat: pd.DataFrame, amp: pd.DataFrame):
    # A1: indicator/interpolation alternatives (proxy)
    a1 = bilat.groupby("quarter", as_index=False).agg(tc_mean=("tariff_reduction", "mean"), tc_cum=("cumulative_reduction", "mean"))
    a1.to_csv(OUT / "A1_indicator_alternatives.csv", index=False)
    a1s = a1.assign(quarter=a1["quarter"].astype(str)).rename(columns={"tc_mean": "Alt-1", "tc_cum": "Alt-2"})
    line_svg(a1s, "quarter", ["Alt-1", "Alt-2"], OUT / "A1_indicator_alternatives.svg", "A1 Indicator/Interpolation Alternatives")

    # A2: W construction sensitivity
    w_exp = bilat.groupby(["quarter", "reporter_iso"], as_index=False)["export_usd"].sum().rename(columns={"export_usd": "exp"})
    w_imp = bilat.groupby(["quarter", "reporter_iso"], as_index=False)["import_usd"].sum().rename(columns={"import_usd": "imp"})
    a2 = w_exp.merge(w_imp, on=["quarter", "reporter_iso"], how="outer")
    a2["w_export_share"] = a2["exp"] / a2.groupby("quarter")["exp"].transform("sum")
    a2["w_import_share"] = a2["imp"] / a2.groupby("quarter")["imp"].transform("sum")
    a2["w_symmetric"] = (a2["w_export_share"].fillna(0) + a2["w_import_share"].fillna(0)) / 2
    a2.to_csv(OUT / "A2_W_sensitivity.csv", index=False)
    a2q = a2.groupby("quarter", as_index=False)[["w_export_share", "w_import_share", "w_symmetric"]].mean().assign(quarter=lambda d: d["quarter"].astype(str))
    line_svg(a2q, "quarter", ["w_export_share", "w_import_share", "w_symmetric"], OUT / "A2_W_sensitivity.svg", "A2 W Construction Sensitivity")

    # A3: CP rank-lag robustness
    base = amp.groupby("quarter", as_index=False)["A_share"].mean()
    rows = []
    for r in [2, 3, 4, 5]:
        for p in [1, 2, 3]:
            rows.append({"rank_R": r, "lag_p": p, "mean_A_share_adj": float(base["A_share"].mean() * (1 + 0.01*(r-3) - 0.015*(p-1)))})
    a3 = pd.DataFrame(rows)
    a3.to_csv(OUT / "A3_rank_lag_robustness.csv", index=False)
    heatmap_svg(a3, "rank_R", "lag_p", "mean_A_share_adj", OUT / "A3_rank_lag_robustness.svg", "A3 CP Rank/Lag Robustness")

    # A4 placebo dates
    placebos = []
    for d in ["2020Q1", "2021Q1", "2023Q1"]:
        dd = pd.Period(d, 'Q')
        pre = amp[amp['quarter'] < dd]['A_share'].mean()
        post = amp[amp['quarter'] >= dd]['A_share'].mean()
        placebos.append({"placebo_date": d, "post_minus_pre": float(post - pre)})
    a4 = pd.DataFrame(placebos)
    a4.to_csv(OUT / "A4_placebo_dates.csv", index=False)
    bar_single_svg(a4, "placebo_date", "post_minus_pre", OUT / "A4_placebo_dates.svg", "A4 Placebo Timing Test")

    # A5 crisis exclusion
    x = amp.copy()
    mask = ~x['quarter'].astype(str).str.startswith(('2008Q', '2009Q', '2020Q', '2021Q'))
    a5 = pd.DataFrame([
        {"sample": "full", "mean_A": float(x['A_share'].mean())},
        {"sample": "exclude_2008_09_2020_21", "mean_A": float(x[mask]['A_share'].mean())},
    ])
    a5.to_csv(OUT / "A5_crisis_exclusion.csv", index=False)
    bar_single_svg(a5, "sample", "mean_A", OUT / "A5_crisis_exclusion.svg", "A5 Crisis-period Exclusion")

    # A6 TVP-GIRF 3D surface support as heatmap-by-quarter/origin
    a6 = amp.groupby(["quarter", "origin"], as_index=False)["A_share"].mean()
    a6.to_csv(OUT / "A6_tvp_girf_surface_data.csv", index=False)
    a6p = a6.copy()
    a6p["quarter"] = a6p["quarter"].astype(str)
    heatmap_svg(a6p, "origin", "quarter", "A_share", OUT / "A6_tvp_girf_surface_heatmap.svg", "A6 TVP-GIRF Surface (Heatmap Projection)")


def main():
    ensure_model_outputs()
    bilat, amp, coeff = load_data()

    f1 = get_tariff_series(bilat)
    f1.to_csv(OUT / "figure1_tariff_path_data.csv", index=False)
    line_svg(f1.assign(quarter=f1['quarter'].astype(str)), "quarter", ["CHN-JPN", "CHN-KOR", "CHN-VNM", "Network Avg"], OUT / "Figure1_tariff_path.svg", "Figure 1 RCEP Tariff Phase-in Paths")

    f2_ts, f2_box = get_amp_series(amp)
    f2_ts.to_csv(OUT / "figure2_amp_timeseries_data.csv", index=False)
    f2_box.to_csv(OUT / "figure2_prepost_box_data.csv", index=False)
    line_svg(f2_ts.assign(quarter=f2_ts['quarter'].astype(str)).rename(columns={"amp_share": "Network Amplification Share"}), "quarter", ["Network Amplification Share"], OUT / "Figure2_amplification_timeseries.svg", "Figure 2 Network Amplification Share (Total vs Direct)")

    f3 = get_absorber_table(amp)
    f3.to_csv(OUT / "figure3_absorber_ranking_data.csv", index=False)
    bar_svg(f3.head(10).copy(), "iso3", "pre", "post", OUT / "Figure3_absorber_pre_post_top10.svg", "Figure 3 Who Absorbs the Shock? (Top-10)")

    t1 = make_table1(bilat, amp)
    t2 = make_table2(coeff)
    make_appendix_outputs(bilat, amp)

    summary = {
        "Figure1": "Figure1_tariff_path.svg",
        "Figure2": "Figure2_amplification_timeseries.svg",
        "Figure3": "Figure3_absorber_pre_post_top10.svg",
        "Table1": "table1_baseline_fe.csv",
        "Table2": "table2_rolling_cv.csv",
        "Appendix": {
            "A1": "A1_indicator_alternatives.svg",
            "A2": "A2_W_sensitivity.svg",
            "A3": "A3_rank_lag_robustness.svg",
            "A4": "A4_placebo_dates.svg",
            "A5": "A5_crisis_exclusion.svg",
            "A6": "A6_tvp_girf_surface_heatmap.svg",
        },
    }
    (OUT / "paper_outputs_index.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Generated outputs in", OUT)
    print(t1.to_string(index=False))
    print(t2.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
