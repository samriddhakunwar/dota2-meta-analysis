import plotly.graph_objects as go
import streamlit as st

import ui

patch = ui.patch()
syn = ui.load("hero_synergy")

ui.header("Synergy Explorer", "Pick a hero to see which teammates lift its win rate, and which drag it down, "
                              "compared with what the two heroes' individual strength predicts.")
left, right = st.columns([3, 2], vertical_alignment="bottom")
pooled = right.toggle("Pool all patches", value=True, help="More games per pair, so narrower confidence intervals.")
scope = "All patches" if pooled else patch
s = syn.query("patch_name == @scope")
heroes = sorted(set(s.hero_a_name) | set(s.hero_b_name))
hero = left.selectbox("Hero", heroes, help="Type to search.")

p = s.query("hero_a_name == @hero or hero_b_name == @hero").assign(
    partner=lambda x: x.hero_b_name.where(x.hero_a_name == hero, x.hero_a_name))
st.subheader(f"{hero}: best and worst partners")
st.caption(f"Scope: {'all patches pooled' if pooled else f'patch {patch}'} · same-team pairs with 50+ games together.")

if p.empty:
    st.info("No partner reaches 50 games with this hero in this scope. Try pooling all patches.")
else:
    p = ui.pct(p, ["win_rate", "expected_win_rate", "lift", "ci_low", "ci_high"])
    best, worst = p.nlargest(10, "lift"), p.nsmallest(10, "lift")
    c = p.loc[best.index.union(worst.index)].sort_values("lift")  # union: no duplicates when < 20 partners
    fig = go.Figure([
        go.Scatter(x=c.expected_win_rate, y=c.partner, mode="markers", name="Expected",
                   marker=dict(symbol="line-ns", size=16, line=dict(width=3, color=ui.INK)),
                   hovertemplate="Expected %{x:.1f}%<extra></extra>"),
        *[go.Scatter(x=g.win_rate, y=g.partner, mode="markers", name=label.capitalize(),
                     marker=dict(size=11, color=ui.LABEL_COLORS[label], line=dict(width=1.5, color=ui.SURFACE)),
                     error_x=dict(type="data", symmetric=False, array=g.ci_high - g.win_rate,
                                  arrayminus=g.win_rate - g.ci_low, color=ui.LABEL_COLORS[label], thickness=1.5,
                                  width=0),
                     customdata=g[["games", "ci_low", "ci_high", "lift"]],
                     hovertemplate="<b>" + hero + " + %{y}</b><br>Observed %{x:.1f}% over %{customdata[0]:,} games"
                                   "<br>95% CI %{customdata[1]:.1f}–%{customdata[2]:.1f}%"
                                   "<br>Lift %{customdata[3]:+.1f} pp<extra>" + label + "</extra>")
          for label, g in c.groupby("label")]])
    fig.add_vline(x=50, line_dash="dot", line_color=ui.GRID)
    fig.update_layout(xaxis_title="Win rate together",
                      xaxis_ticksuffix="%", yaxis=dict(showgrid=False, categoryorder="array", categoryarray=c.partner),
                      hovermode="closest")
    ui.chart(fig, 80 + 28 * len(c), title="Observed win rate (with 95% CI) vs. expected")

    cols = ["partner", "games", "win_rate", "expected_win_rate", "lift", "label"]
    cfg = {"partner": ui.TEXT("Partner"), "games": ui.INT("Games"), "win_rate": ui.PCT("Win rate"),
           "expected_win_rate": ui.PCT("Expected", help="Predicted from both heroes' individual win rates"),
           "lift": st.column_config.NumberColumn("Lift", format="%+.1f pp", help="Observed − expected"),
           "label": ui.TEXT("Verdict", help="Synergy / anti-synergy only if the 95% CI excludes the expected rate")}
    tab_best, tab_worst = st.tabs(["Best partners", "Worst partners"])
    for tab, t in [(tab_best, best), (tab_worst, worst)]:
        tab.dataframe(t.assign(label=lambda x: ui.verdict(x.label)), hide_index=True, column_order=cols,
                      column_config=cfg)

ui.explain(
    "**Expected** is what the pair should win if the two heroes' individual edges simply add up (combined on the "
    "log-odds scale). **Lift** is observed minus expected, in percentage points. A pair is 🔵 **synergy** or "
    "🟠 **anti-synergy** only if its 95% confidence interval misses the expected mark. Across all pairs only about "
    "5% are flagged, which is roughly what chance alone produces, so treat any single pair as a lead, not proof.")
