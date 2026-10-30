import plotly.graph_objects as go
import streamlit as st

import ui

patch = ui.patch()
meta = ui.load("meta_per_patch")
heroes = sorted(meta.hero_name.unique())
default = meta.query("patch_name == @patch").nlargest(1, "contest_rate").hero_name.iloc[0]

ui.header("Hero Lookup", "One hero across every patch: how often it is picked or banned, and whether it wins.")
st.session_state.setdefault("hero", default)  # first visit: most-contested hero; later: keep the user's choice
hero = st.selectbox("Hero", heroes, key="hero", help="Type to search.")

h = meta.query("hero_name == @hero").merge(
    ui.load("winrate_vs_pickrate")[["patch_id", "hero_id", "ci_low", "ci_high", "label"]],
    on=["patch_id", "hero_id"], how="left").sort_values("patch_id")

# ---- KPI row: selected hero in the selected patch
st.subheader(f"{hero} in patch {patch}")
row = h.query("patch_name == @patch")
if row.empty:
    st.info(f"{hero} was never picked or banned in patch {patch}.")
else:
    r = row.iloc[0]
    with st.container(horizontal=True):
        st.metric("Contest rate", f"{r.contest_rate:.1%}", border=True, help="Picked or banned, % of matches")
        st.metric("Pick rate", f"{r.pick_rate:.1%}", border=True, help=f"{r.picks:,} picks")
        st.metric("Ban rate", f"{r.ban_rate:.1%}", border=True, help=f"{r.bans:,} bans")
        st.metric("Win rate", f"{r.win_rate:.1%}" if r.picks else "–", border=True,
                  help=ui.ci_text(r.ci_low, r.ci_high) if r.ci_low == r.ci_low else "No CI: under 100 picks")
        st.metric("Verdict", ui.verdict(row.label).iloc[0], border=True)

# ---- trends
rates = ui.pct(h, ["contest_rate", "pick_rate", "ban_rate"])
fig = go.Figure([go.Scatter(x=rates.patch_name, y=rates[c], name=n, mode="lines+markers",
                            line=dict(color=col, width=2, dash=dash), marker=dict(size=8),
                            hovertemplate=f"{n}: " + "%{y:.1f}%<extra></extra>")
                 for c, n, col, dash in [("contest_rate", "Contest rate", ui.INK, "solid"),
                                         ("pick_rate", "Pick rate", ui.BLUE, "solid"),
                                         ("ban_rate", "Ban rate", ui.ORANGE, "solid")]])
fig.update_layout(hovermode="x unified", xaxis_title="Patch",
                  yaxis_title="% of matches", xaxis_type="category", yaxis_ticksuffix="%", yaxis_rangemode="tozero",
                  legend_y=1.0)
ui.chart(fig, 380, title="How often is it picked or banned?")

w = ui.pct(h, ["win_rate", "ci_low", "ci_high"])
fig = go.Figure(go.Scatter(
    x=w.patch_name, y=w.win_rate, mode="lines+markers", line=dict(color=ui.GRAY, width=2),
    marker=dict(size=11, color=[ui.LABEL_COLORS.get(lab, ui.GRAY) for lab in w.label],
                line=dict(width=1.5, color=ui.SURFACE)),
    error_y=dict(type="data", symmetric=False, array=w.ci_high - w.win_rate, arrayminus=w.win_rate - w.ci_low,
                 color=ui.INK_2, thickness=1.5, width=4),
    customdata=w[["picks", "ci_low", "ci_high"]].assign(v=ui.verdict(h.label)),
    hovertemplate="Patch %{x}<br>Win rate %{y:.1f}% · %{customdata[0]:,} picks<br>"
                  "95% CI %{customdata[1]:.1f}–%{customdata[2]:.1f}%<br>%{customdata[3]}<extra></extra>"))
fig.add_hline(y=50, line_dash="dot", line_color=ui.INK_2)
fig.update_layout(xaxis_title="Patch",
                  yaxis_title="Win rate when picked", xaxis_type="category", yaxis_ticksuffix="%")
ui.chart(fig, 360, title="Does it win? (95% CI shown for patches with 100+ picks)")

st.dataframe(ui.pct(h, ["contest_rate", "pick_rate", "ban_rate", "win_rate"])
             .assign(label=lambda x: ui.verdict(x.label),
                     ci=(h.ci_low * 100).map("{:.1f}".format) + "–" + (h.ci_high * 100).map("{:.1f}%".format))
             .assign(ci=lambda x: x.ci.where(h.ci_low.notna(), "")),
             hide_index=True,
             column_order=["patch_name", "matches", "picks", "bans", "contest_rate", "pick_rate", "ban_rate",
                           "win_rate", "ci", "label"],
             column_config={"patch_name": ui.TEXT("Patch"), "matches": ui.INT("Matches"), "picks": ui.INT("Picks"),
                            "bans": ui.INT("Bans"), "contest_rate": ui.BAR("Contest rate"),
                            "pick_rate": ui.PCT("Pick rate"), "ban_rate": ui.PCT("Ban rate"),
                            "win_rate": ui.PCT("Win rate"), "ci": ui.TEXT("95% CI"),
                            "label": ui.TEXT("Verdict")})

ui.explain(
    "The top chart shows how much teams care about the hero: **pick rate** + **ban rate** = **contest rate**, "
    "each as a share of all matches in the patch. The bottom chart shows its win rate when picked; the bars are "
    "the **95% confidence interval**, the range the true win rate plausibly lies in. If a bar crosses the 50% line, "
    "the hero is statistically indistinguishable from a coin flip in that patch.")
