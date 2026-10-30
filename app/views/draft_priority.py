import plotly.graph_objects as go
import streamlit as st

import ui

patch = ui.patch()
draft = ui.load("draft_priority").query("patch_name == @patch")

ui.header(f"First-phase draft priority · patch {patch}",
          "Which heroes do teams grab or deny in the opening phase of the draft (7 bans, then 2 picks)?")

d = ui.pct(draft.head(20), ["p1_pick_rate", "p1_ban_rate", "p1_contest_rate"]).iloc[::-1]
fig = go.Figure([go.Bar(x=d[c], y=d.hero_name, orientation="h", name=n, marker=dict(color=col, line_width=0),
                        customdata=d[["p1_contest_rate", cnt]],
                        hovertemplate="<b>%{y}</b><br>" + n + ": %{x:.1f}% of matches (%{customdata[1]:,})"
                                      "<br>First-phase contest: %{customdata[0]:.1f}%<extra></extra>")
                 for c, cnt, n, col in [("p1_pick_rate", "p1_picks", "First-phase pick", ui.BLUE),
                                        ("p1_ban_rate", "p1_bans", "First-phase ban", ui.ORANGE)]])
fig.update_layout(barmode="stack", bargap=0.25,
                  xaxis_title="% of matches", xaxis_ticksuffix="%", yaxis_showgrid=False, legend_traceorder="normal")
ui.chart(fig, 620, title="Top 20 heroes by first-phase contest rate")

st.caption("All columns except *All picks* count the first phase only.")

st.dataframe(ui.pct(draft, ["p1_contest_rate", "p1_pick_rate", "p1_ban_rate", "p1_pick_share"]), hide_index=True,
             column_order=["hero_name", "p1_contest_rate", "p1_pick_rate", "p1_ban_rate", "p1_picks", "p1_bans",
                           "picks", "p1_pick_share"],
             column_config={
                 "hero_name": ui.TEXT("Hero"),
                 "p1_contest_rate": ui.BAR("Contest", max_value=float(draft.p1_contest_rate.max() * 100),
                                           help="Picked or banned in phase 1, % of matches"),
                 "p1_pick_rate": ui.PCT("Pick rate"), "p1_ban_rate": ui.PCT("Ban rate"),
                 "p1_picks": ui.INT("Picks"), "p1_bans": ui.INT("Bans"),
                 "picks": ui.INT("All picks", help="Picks in any phase"),
                 "p1_pick_share": ui.PCT("Early-pick share", help="Share of this hero's picks made in phase 1")})

ui.explain(
    "A Captains Mode draft has three phases; **phase 1** is the first nine draft slots: seven bans, then two picks. What "
    "teams spend these slots on shows what they fear or want most. **First-phase contest rate** is the share of "
    "matches where the hero was picked or banned in phase 1. A long orange bar means teams deny the hero rather "
    "than play it.")
