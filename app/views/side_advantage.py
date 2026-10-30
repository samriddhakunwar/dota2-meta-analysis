import plotly.graph_objects as go
import streamlit as st

import ui

patch = ui.patch()
s = ui.load("side_advantage")
per = ui.pct(s.dropna(subset=["patch_id"]).sort_values("patch_id"), ["radiant_win_rate", "ci_low", "ci_high"])
sel = per.query("patch_name == @patch").iloc[0]
total = s.query("patch_name == 'All patches'").iloc[0]
clear = per.query("ci_low > 50")

ui.header("Side advantage", "Does the Radiant side win more often than Dire, and does that change from patch to patch?")
with st.container(horizontal=True):
    st.metric(f"Radiant win rate · {patch}", f"{sel.radiant_win_rate:.1f}%", border=True,
              help=f"95% CI {sel.ci_low:.1f}–{sel.ci_high:.1f}% over {sel.matches:,} matches")
    st.metric("Radiant win rate · all patches", f"{total.radiant_win_rate:.1%}", border=True,
              help=f"{ui.ci_text(total.ci_low, total.ci_high)} over {total.matches:,} matches")
    st.metric("Patches with a clear Radiant edge", f"{len(clear)} of {len(per)}", border=True,
              help="Whole 95% CI above 50%")

fig = go.Figure([
    go.Scatter(x=list(per.patch_name) + list(per.patch_name[::-1]), y=list(per.ci_high) + list(per.ci_low[::-1]),
               fill="toself", mode="lines", line_width=0, fillcolor="rgba(57,135,229,0.18)", name="95% CI",
               hoverinfo="skip"),
    go.Scatter(x=per.patch_name, y=per.radiant_win_rate, mode="lines+markers", line=dict(color=ui.BLUE, width=2),
               marker=dict(size=8), name="Radiant win rate", customdata=per[["ci_low", "ci_high", "matches"]],
               hovertemplate="Patch %{x}<br>Radiant win rate %{y:.1f}%<br>95% CI %{customdata[0]:.1f}–"
                             "%{customdata[1]:.1f}%<br>%{customdata[2]:,} matches<extra></extra>"),
    go.Scatter(x=[patch], y=[sel.radiant_win_rate], mode="markers", name=f"Selected patch ({patch})",
               marker=dict(size=16, color=ui.ACCENT, line=dict(width=2, color=ui.SURFACE)), hoverinfo="skip")])
fig.add_hline(y=50, line_dash="dot", line_color=ui.INK_2, annotation_text="50% = no side advantage",
              annotation_position="bottom right", annotation_font_color=ui.INK_2)
fig.update_layout(yaxis_title="Radiant win rate", yaxis_ticksuffix="%",
                  xaxis_title="Patch", xaxis_type="category")
ui.chart(fig, 420, title="Radiant win rate by patch")

st.dataframe(ui.pct(s, ["radiant_win_rate", "ci_low", "ci_high"]), hide_index=True,
             column_order=["patch_name", "matches", "radiant_wins", "radiant_win_rate", "ci_low", "ci_high"],
             column_config={"patch_name": ui.TEXT("Patch"), "matches": ui.INT("Matches"),
                            "radiant_wins": ui.INT("Radiant wins"), "radiant_win_rate": ui.PCT("Radiant win rate"),
                            "ci_low": ui.PCT("CI low"), "ci_high": ui.PCT("CI high")})

ui.explain(
    "Each match has a Radiant and a Dire side. If sides didn't matter, Radiant would win 50% of the time. The "
    "shaded band is the **95% confidence interval**: where the band sits entirely above the dotted 50% line, the "
    "Radiant edge in that patch is real rather than luck. Note that teams choose side and first pick together, so "
    "part of the edge may come from that choice.")
