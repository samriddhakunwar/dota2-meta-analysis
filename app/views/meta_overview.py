import plotly.graph_objects as go
import streamlit as st

import ui

patch = ui.patch()
side_all = ui.load("side_advantage")
side = side_all.query("patch_name == @patch").iloc[0]
total = side_all.query("patch_name == 'All patches'").iloc[0]
meta = ui.load("meta_per_patch").query("patch_name == @patch")
wr = ui.load("winrate_vs_pickrate").query("patch_name == @patch")
draft = ui.load("draft_priority").query("patch_name == @patch")
pairs = ui.load("hero_synergy").query("patch_name == 'All patches'")

ui.header("Dota 2 Pro Meta & Draft Analysis",
          f"Which heroes do pro teams fight over, which actually win, and what is just noise? "
          f"{total.matches:,} Captains Mode pro matches across {len(ui.patch_names())} patches. "
          f"Showing patch **{patch}**: change it in the sidebar.")

with st.container(horizontal=True):
    st.metric("Matches in patch", f"{side.matches:,}", border=True,
              help=f"Out of {total.matches:,} matches across all patches.")
    st.metric("Patches covered", len(ui.patch_names()), border=True,
              help=f"{ui.patch_names()[0]} to {ui.patch_names()[-1]}, Jan 2024 – Sep 2026.")
    st.metric("Heroes picked at least once", int((meta.picks > 0).sum()), border=True)
    st.metric("Radiant win rate", f"{side.radiant_win_rate:.1%}", border=True,
              help=ui.ci_text(side.ci_low, side.ci_high))
st.caption(f"{side.matches:,} of {total.matches:,} matches in total. Hover a card's ⓘ for details.")

# ---- key findings, computed from the tables so they follow the selected patch
st.subheader("Key findings")
top = wr.nlargest(1, "pick_rate").iloc[0]
best = wr.query("label == 'overperformer'").nlargest(1, "ci_low")
traps = wr.query("label == 'trap pick'").sort_values("pick_rate", ascending=False)
p1 = draft.iloc[0]
flagged = (pairs.label != "within noise").mean()
coin_flip = "no better than a coin flip" if top.ci_low <= 0.5 <= top.ci_high else (
    "clearly above 50%" if top.ci_low > 0.5 else "clearly below 50%")

cards = [
    (":material/trending_up:", "Popular ≠ winning",
     f"**{top.hero_name}** is the most-picked hero ({top.pick_rate:.1%} of matches) but wins "
     f"**{top.win_rate:.1%}** ({ui.ci_text(top.ci_low, top.ci_high)}): {coin_flip}."),
    (":material/diamond:", "Hidden strength vs. trap picks",
     (f"**{best.hero_name.iloc[0]}** is the most reliable overperformer: {best.win_rate.iloc[0]:.1%} wins at a "
      f"{best.pick_rate.iloc[0]:.1%} pick rate. " if len(best) else "No hero clears 50% with confidence. ")
     + (f"Trap picks (popular, but losing): **{', '.join(traps.hero_name)}**." if len(traps)
        else "No trap picks in this patch.")),
    (":material/block:", "The first phase is about denial",
     f"**{p1.hero_name}** is the top first-phase hero ({p1.p1_contest_rate:.1%} of matches): "
     f"**{p1.p1_bans:,} bans** vs. only {p1.p1_picks:,} picks."),
    (":material/casino:", "Most “synergy” is noise",
     f"Only **{flagged:.1%}** of {len(pairs):,} hero pairs (all patches) beat or miss their expected win rate with "
     f"confidence: about the 5% you'd flag by pure chance."),
]
for row in (cards[:2], cards[2:]):  # 2x2 grid: readable at both desktop and narrow widths
    for col, (icon, title, body) in zip(st.columns(2), row):
        with col.container(border=True, height="stretch"):
            st.markdown(f"##### {icon} {title}")
            st.markdown(body)

# ---- win rate vs pick rate
st.subheader("Win rate vs. pick rate")
st.caption("Heroes with 100+ picks in the patch. Hover a dot for the hero's 95% confidence interval.")
w = ui.pct(wr, ["pick_rate", "win_rate", "ci_low", "ci_high"])
fig = go.Figure([go.Scatter(
    x=g.pick_rate, y=g.win_rate, mode="markers", name=label,
    marker=dict(size=10, color=ui.LABEL_COLORS[label], line=dict(width=1.5, color=ui.SURFACE)),
    customdata=g[["hero_name", "ci_low", "ci_high", "picks"]],
    hovertemplate="<b>%{customdata[0]}</b><br>Pick rate %{x:.1f}% · %{customdata[3]:,} picks<br>"
                  "Win rate %{y:.1f}% (95% CI %{customdata[1]:.1f}–%{customdata[2]:.1f}%)<extra>" + label + "</extra>")
    for label, g in w.groupby("label") if label in ["within noise", "overperformer", "trap pick"]])
# draw noise first so the coloured verdicts sit on top
fig.data = sorted(fig.data, key=lambda t: t.name != "within noise")
fig.add_hline(y=50, line_dash="dot", line_color=ui.INK_2, annotation_text="50% = coin flip",
              annotation_position="bottom right", annotation_font_color=ui.INK_2)
fig.update_layout(xaxis_title="Pick rate (% of matches)", yaxis_title="Win rate when picked",
                  xaxis_ticksuffix="%", yaxis_ticksuffix="%")
ui.chart(fig, 460)

# ---- most contested table
st.subheader("Most contested heroes")
t = ui.pct(meta, ["contest_rate", "pick_rate", "ban_rate", "win_rate"]).merge(
    wr[["hero_id", "label"]], on="hero_id", how="left").head(30).assign(label=lambda x: ui.verdict(x.label))
st.dataframe(t, hide_index=True, column_order=["hero_name", "contest_rate", "pick_rate", "ban_rate", "picks",
                                               "win_rate", "label"],
             column_config={"hero_name": ui.TEXT("Hero"),
                            "contest_rate": ui.BAR("Contest rate", help="Picked or banned, % of matches"),
                            "pick_rate": ui.PCT("Pick rate"), "ban_rate": ui.PCT("Ban rate"),
                            "picks": ui.INT("Picks"), "win_rate": ui.PCT("Win rate"),
                            "label": ui.TEXT("Verdict", help="Based on the 95% CI of the win rate (100+ picks)")})

ui.explain(
    "**Contest rate** is the share of matches where a hero was picked *or* banned: how much teams care about it. "
    "**Win rate** is wins ÷ picks, and the **95% confidence interval (Wilson CI)** is the range the true win rate "
    "plausibly lies in given how many games we have. A hero is an 🔵 **overperformer** only if the whole interval "
    "is above 50%, and a 🟠 **trap pick** if it's popular (top quarter by pick rate) but the whole interval is "
    "below 50%. Everything else is ⚪ **within noise**.")
