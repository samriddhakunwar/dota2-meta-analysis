"""Dota 2 Pro Meta & Draft dashboard. Reads only the small aggregated tables in data/app/ (committed to git)."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "app"
BLUE, ORANGE, RED, MUTED = "#2a78d6", "#eb6834", "#e34948", "#898781"

st.set_page_config(page_title="Dota 2 Pro Meta", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


def pct(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Rates as percentages, for display."""
    return df.assign(**{c: df[c] * 100 for c in cols})


patches = load("patches").query("included").sort_values("patch_id")
page = st.sidebar.radio("Page", ["Meta Overview", "Hero Lookup", "Draft Priority", "Synergy Explorer", "Side Advantage"])
patch = st.sidebar.selectbox("Patch", patches.patch_name[::-1].tolist())
st.sidebar.caption("Captains Mode pro matches, Jan 2024 - Sep 2026. "
                   "Source: Kaggle 'Dota 2 Pro League Matches' (bwandowando).")

if page == "Meta Overview":
    st.title(f"Meta overview: patch {patch}")
    meta = load("meta_per_patch").query("patch_name == @patch")
    side = load("side_advantage").query("patch_name == @patch").iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Matches", f"{int(side.matches):,}")
    c2.metric("Heroes picked at least once", int((meta.picks > 0).sum()))
    c3.metric("Radiant win rate", f"{side.radiant_win_rate:.1%}")

    wr = load("winrate_vs_pickrate").query("patch_name == @patch")
    st.subheader("Win rate vs. pick rate (heroes with 100+ picks)")
    fig = px.scatter(pct(wr, ["pick_rate", "win_rate", "ci_low", "ci_high"]), x="pick_rate", y="win_rate",
                     color="label", hover_name="hero_name",
                     color_discrete_map={"within noise": MUTED, "overperformer": BLUE, "trap pick": ORANGE},
                     error_y=wr.ci_high * 100 - wr.win_rate * 100, error_y_minus=wr.win_rate * 100 - wr.ci_low * 100,
                     labels={"pick_rate": "Pick rate (%)", "win_rate": "Win rate (%)"})
    fig.add_hline(y=50, line_dash="dash", line_color=MUTED)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Most contested heroes")
    st.dataframe(pct(meta, ["contest_rate", "pick_rate", "ban_rate", "win_rate"])
                 [["hero_name", "contest_rate", "pick_rate", "ban_rate", "picks", "win_rate"]].head(30),
                 hide_index=True, column_config={c: st.column_config.NumberColumn(format="%.1f%%")
                                                 for c in ["contest_rate", "pick_rate", "ban_rate", "win_rate"]})

elif page == "Hero Lookup":
    meta = load("meta_per_patch")
    hero = st.selectbox("Hero", sorted(meta.hero_name.unique()))
    st.title(f"{hero} across patches")
    h = meta.query("hero_name == @hero").merge(
        load("winrate_vs_pickrate")[["patch_id", "hero_id", "ci_low", "ci_high", "label"]],
        on=["patch_id", "hero_id"], how="left").sort_values("patch_id")
    rates = h.melt(id_vars="patch_name", value_vars=["contest_rate", "pick_rate", "ban_rate"], var_name="metric")
    st.plotly_chart(px.line(pct(rates, ["value"]), x="patch_name", y="value", color="metric", markers=True,
                            color_discrete_sequence=[BLUE, ORANGE, MUTED],
                            labels={"value": "% of matches", "patch_name": "Patch"}), width="stretch")
    fig = go.Figure(go.Scatter(x=h.patch_name, y=h.win_rate * 100, mode="lines+markers", line_color=BLUE,
                               error_y=dict(type="data", symmetric=False, array=(h.ci_high - h.win_rate) * 100,
                                            arrayminus=(h.win_rate - h.ci_low) * 100)))
    fig.add_hline(y=50, line_dash="dash", line_color=MUTED)
    fig.update_layout(title="Win rate when picked (95% CI shown for patches with 100+ picks)",
                      yaxis_title="Win rate (%)", xaxis_title="Patch")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(pct(h, ["contest_rate", "pick_rate", "ban_rate", "win_rate", "ci_low", "ci_high"])
                 [["patch_name", "matches", "picks", "bans", "contest_rate", "pick_rate", "ban_rate", "win_rate",
                   "ci_low", "ci_high", "label"]], hide_index=True)

elif page == "Draft Priority":
    st.title(f"First-phase draft priority: patch {patch}")
    st.caption("Phase 1 = draft slots 0-8 (7 bans, then 2 picks). Rates are shares of all matches in the patch.")
    d = load("draft_priority").query("patch_name == @patch").head(20).iloc[::-1]
    fig = go.Figure([go.Bar(x=d[c] * 100, y=d.hero_name, orientation="h", name=n, marker_color=col)
                     for c, n, col in [("p1_pick_rate", "first-phase pick", BLUE), ("p1_ban_rate", "first-phase ban", ORANGE)]])
    fig.update_layout(barmode="stack", height=600, xaxis_title="% of matches", legend_traceorder="normal")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(pct(load("draft_priority").query("patch_name == @patch"),
                     ["p1_contest_rate", "p1_pick_rate", "p1_ban_rate", "p1_pick_share"])
                 [["hero_name", "p1_contest_rate", "p1_pick_rate", "p1_ban_rate", "p1_picks", "p1_bans", "picks",
                   "p1_pick_share"]], hide_index=True)

elif page == "Synergy Explorer":
    syn = load("hero_synergy")
    pooled = st.checkbox("Pool all patches (more games per pair)", value=True)
    scope = "All patches" if pooled else patch
    s = syn.query("patch_name == @scope")
    heroes = sorted(set(s.hero_a_name) | set(s.hero_b_name))
    hero = st.selectbox("Hero", heroes)
    st.title(f"{hero}: best and worst partners ({scope})")
    st.caption("Same-team pairs with at least 50 games together. Expected = combine both heroes' individual win rates "
               "on the log-odds scale. Lift = observed - expected. Most lifts are within sampling noise: only pairs "
               "labelled synergy / anti-synergy have a 95% CI that excludes the expected rate.")
    p = s.query("hero_a_name == @hero or hero_b_name == @hero").assign(
        partner=lambda x: x.hero_b_name.where(x.hero_a_name == hero, x.hero_a_name))
    p = pct(p, ["win_rate", "expected_win_rate", "lift", "ci_low", "ci_high"])
    cols = ["partner", "games", "win_rate", "expected_win_rate", "lift", "ci_low", "ci_high", "label"]
    fmt = {c: st.column_config.NumberColumn(format="%.1f") for c in cols[2:7]}
    left, right = st.columns(2)
    left.subheader("Best partners")
    left.dataframe(p.nlargest(10, "lift")[cols], hide_index=True, column_config=fmt)
    right.subheader("Worst partners")
    right.dataframe(p.nsmallest(10, "lift")[cols], hide_index=True, column_config=fmt)
    if p.empty:
        st.info("No partner reaches 50 games with this hero in this scope.")

else:
    st.title("Side advantage: Radiant win rate by patch")
    s = load("side_advantage")
    per = s.dropna(subset=["patch_id"]).sort_values("patch_id")
    fig = go.Figure([
        go.Scatter(x=list(per.patch_name) + list(per.patch_name[::-1]), y=list(per.ci_high * 100) + list(per.ci_low[::-1] * 100),
                   fill="toself", mode="lines", line_width=0, fillcolor="rgba(42,120,214,0.15)", name="95% CI"),
        go.Scatter(x=per.patch_name, y=per.radiant_win_rate * 100, mode="lines+markers", line_color=BLUE,
                   name="Radiant win rate"),
        go.Scatter(x=[patch], y=per.query("patch_name == @patch").radiant_win_rate * 100, mode="markers",
                   marker=dict(size=16, color=ORANGE), name=f"selected: {patch}")])
    fig.add_hline(y=50, line_dash="dash", line_color=MUTED)
    fig.update_layout(yaxis_title="Radiant win rate (%)", xaxis_title="Patch", xaxis_type="category")
    st.plotly_chart(fig, width="stretch")
    st.dataframe(pct(s, ["radiant_win_rate", "ci_low", "ci_high"]).drop(columns="patch_id"), hide_index=True)
