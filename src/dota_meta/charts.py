"""Static Plotly charts for the README, all sharing one style."""
import sys

import duckdb
import plotly.graph_objects as go
import plotly.io as pio

from dota_meta.load import DB, ROOT

FIG = ROOT / "reports" / "figures"

# palette (validated): categorical blue / orange, neutral gray for "everything else", diverging blue <-> red
SURFACE, INK, INK_2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, ORANGE, RED = "#2a78d6", "#eb6834", "#e34948"
SEQ_BLUE = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SOURCE = "Source: Kaggle 'Dota 2 Pro League Matches 2016-2026' (bwandowando), Captains Mode pro matches"

pio.templates["dota"] = go.layout.Template(layout=dict(
    font=dict(family="Segoe UI, Helvetica, Arial, sans-serif", size=13, color=INK_2),
    title=dict(font=dict(size=19, color=INK), x=0.01, xanchor="left", y=0.97, yanchor="top"),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    xaxis=dict(gridcolor=GRID, linecolor=MUTED, zeroline=False, ticks="outside", tickcolor=MUTED, title_standoff=10),
    yaxis=dict(gridcolor=GRID, linecolor=MUTED, zeroline=False, ticks="outside", tickcolor=MUTED, title_standoff=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=80, r=40, t=110, b=105),
))
pio.templates.default = "dota"


def _title(main: str, sub: str) -> str:
    return f"{main}<br><span style='font-size:13px;color:{INK_2}'>{sub}</span>"


def _save(fig: go.Figure, name: str, width: int = 1100, height: int = 650) -> None:
    fig.add_annotation(text=SOURCE, xref="paper", yref="paper", x=0, y=0, yshift=-78, xanchor="left", yanchor="top",
                       showarrow=False, font=dict(size=11, color=MUTED))
    path = FIG / f"{name}.png"
    fig.write_image(path, width=width, height=height, scale=2)
    print(f"wrote {path.relative_to(ROOT)}")


def contest_heatmap(con, top_n: int = 25) -> None:
    df = con.sql(f"""
        WITH top AS (SELECT hero_id FROM meta_per_patch GROUP BY 1
                     ORDER BY sum(contest_rate) DESC LIMIT {top_n})
        SELECT hero_name, patch_name, contest_rate FROM meta_per_patch WHERE hero_id IN (SELECT hero_id FROM top)""").df()
    grid = df.pivot(index="hero_name", columns="patch_name", values="contest_rate").fillna(0)
    grid = grid.loc[grid.mean(axis=1).sort_values().index]  # most contested on top
    fig = go.Figure(go.Heatmap(
        z=grid.values * 100, x=grid.columns, y=grid.index, colorscale=SEQ_BLUE, zmin=0,
        xgap=2, ygap=2, text=(grid.values * 100).round(0).astype(int), texttemplate="%{text}",
        textfont=dict(size=10), colorbar=dict(title=dict(text="Contest rate (%)"), ticksuffix="%", thickness=12),
        hovertemplate="%{y} in %{x}: %{z:.1f}%<extra></extra>"))
    fig.update_layout(title=_title(f"Which heroes defined each patch? Top {top_n} most-contested heroes",
                                   "Contest rate = (picks + bans) / matches in the patch, in %"),
                      xaxis=dict(title="Patch", type="category", showgrid=False),
                      yaxis=dict(title=None, showgrid=False, tickfont=dict(size=12)),
                      margin=dict(l=150, r=40, t=100, b=105))
    _save(fig, "contest_heatmap", height=820)


def winrate_scatter(con) -> None:
    df = con.sql("SELECT * FROM winrate_vs_pickrate WHERE patch_id = (SELECT max(patch_id) FROM winrate_vs_pickrate)").df()
    patch, p75 = df.patch_name.iloc[0], df.pick_rate_p75.iloc[0]
    fig = go.Figure()
    for label, color, size in [("within noise", MUTED, 8), ("overperformer", BLUE, 10), ("trap pick", ORANGE, 10)]:
        d = df[df.label == label]
        fig.add_trace(go.Scatter(
            x=d.pick_rate * 100, y=d.win_rate * 100, mode="markers", name=f"{label} ({len(d)})",
            marker=dict(color=color, size=size, line=dict(color=SURFACE, width=2), opacity=0.55 if label == "within noise" else 1),
            error_y=dict(type="data", symmetric=False, array=(d.ci_high - d.win_rate) * 100,
                         arrayminus=(d.win_rate - d.ci_low) * 100, color=color, thickness=1, width=0),
            text=d.hero_name, hovertemplate="%{text}: %{y:.1f}% win, %{x:.1f}% pick<extra></extra>"))
    fig.add_hline(y=50, line=dict(color=INK_2, width=1, dash="dash"))
    fig.add_vline(x=p75 * 100, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=p75 * 100, y=1, yref="paper", text="top-quartile pick rate", showarrow=False,
                       xanchor="left", yanchor="top", xshift=4, font=dict(size=11, color=MUTED))
    # label: the 6 strongest overperformers, every trap pick, and the 4 most-picked heroes
    show = (df[df.label == "overperformer"].nlargest(6, "ci_low").index.union(df[df.label == "trap pick"].index)
            .union(df.nlargest(4, "pick_rate").index))
    placed = []
    for _, r in df.loc[show].sort_values("pick_rate").iterrows():
        x, y = r.pick_rate * 100, r.win_rate * 100
        # nudge a label up when it would sit on top of a nearby label
        shift = 14 if any(abs(x - px) < 2.5 and abs(y - py) < 1 for px, py in placed) else 0
        placed.append((x, y))
        fig.add_annotation(x=x, y=y, text=r.hero_name, showarrow=False, xanchor="left", xshift=7, yshift=shift,
                           font=dict(size=11, color=INK))
    fig.update_layout(title=_title(f"Popular isn't the same as strong: win rate vs. pick rate, patch {patch}",
                                   "Each dot is a hero with at least 100 picks; bars are Wilson 95% confidence intervals"),
                      xaxis=dict(title="Pick rate (% of matches)", ticksuffix="%", rangemode="tozero"),
                      yaxis=dict(title="Win rate when picked", ticksuffix="%"))
    _save(fig, "winrate_vs_pickrate", height=700)


def diversity_line(con, low_sample: int = 1000) -> None:
    df = con.sql("SELECT * FROM meta_diversity ORDER BY month").df()
    patches = con.sql("""SELECT patch_name, release_time FROM patches
                         WHERE included AND release_time >= (SELECT min(month) FROM meta_diversity)""").df()
    ok, low = df[df.matches >= low_sample], df[df.matches < low_sample]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.month, y=df.effective_heroes, mode="lines", line=dict(color=BLUE, width=2),
                             showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=ok.month, y=ok.effective_heroes, mode="markers", name="effective number of heroes",
                             marker=dict(color=BLUE, size=8, line=dict(color=SURFACE, width=2))))
    fig.add_trace(go.Scatter(x=low.month, y=low.effective_heroes, mode="markers",
                             name=f"month with < {low_sample:,} matches (small sample, biased low)",
                             marker=dict(color=SURFACE, size=9, line=dict(color=BLUE, width=2))))
    for _, p in patches.iterrows():
        fig.add_vline(x=p.release_time, line=dict(color=MUTED, width=1, dash="dot"))
        fig.add_annotation(x=p.release_time, y=1, yref="paper", text=p.patch_name, showarrow=False,
                           xanchor="left", yanchor="top", xshift=3, font=dict(size=11, color=INK_2))
    fig.update_layout(title=_title("How diverse is the pro meta? Effective number of heroes picked per month",
                                   "exp(Shannon entropy) of the monthly pick distribution; dotted lines mark patch releases"),
                      xaxis=dict(title="Month", showgrid=False),
                      yaxis=dict(title="Effective number of heroes", rangemode="tozero"))
    _save(fig, "meta_diversity")


def risers_fallers(con, n: int = 10) -> None:
    df = con.sql(f"""SELECT * FROM patch_shifts WHERE patch_id = (SELECT max(patch_id) FROM patch_shifts)
                     AND (riser_rank <= {n} OR faller_rank <= {n}) ORDER BY contest_rate_change""").df()
    change = df.patch_change.iloc[0]
    fig = go.Figure(go.Bar(
        x=df.contest_rate_change * 100, y=df.hero_name, orientation="h",
        marker=dict(color=[BLUE if v > 0 else RED for v in df.contest_rate_change], line=dict(color=SURFACE, width=2)),
        text=[f"{v:+.0f} pp" for v in df.contest_rate_change * 100], textposition="outside",
        textfont=dict(size=11, color=INK_2), cliponaxis=False,
        customdata=df[["prev_contest_rate", "contest_rate"]].values * 100,
        hovertemplate="%{y}: %{customdata[0]:.0f}% → %{customdata[1]:.0f}%<extra></extra>"))
    fig.add_vline(x=0, line=dict(color=INK_2, width=1))
    fig.update_layout(title=_title(f"Winners and losers of patch {change.split(' → ')[1]}: biggest contest-rate shifts",
                                   f"Change in contest rate from {change.replace(' → ', ' to ')}, percentage points; "
                                   f"top {n} risers (blue) and fallers (red)"),
                      xaxis=dict(title="Change in contest rate (percentage points)", ticksuffix=" pp"),
                      yaxis=dict(title=None, showgrid=False), bargap=0.25, showlegend=False,
                      margin=dict(l=150, r=60, t=100, b=105))
    _save(fig, "risers_fallers", height=720)


def draft_priority(con, n: int = 15) -> None:
    df = con.sql(f"""SELECT * FROM draft_priority WHERE patch_id = (SELECT max(patch_id) FROM draft_priority)
                     ORDER BY p1_contest_rate DESC LIMIT {n}""").df().iloc[::-1]  # top hero on top
    patch = df.patch_name.iloc[0]
    fig = go.Figure()
    for col, name, color in [("p1_pick_rate", "first-phase pick", BLUE), ("p1_ban_rate", "first-phase ban", ORANGE)]:
        fig.add_trace(go.Bar(x=df[col] * 100, y=df.hero_name, orientation="h", name=name,
                             marker=dict(color=color, line=dict(color=SURFACE, width=2)),
                             hovertemplate="%{y}: %{x:.1f}% of matches<extra>" + name + "</extra>"))
    fig.add_trace(go.Scatter(x=df.p1_contest_rate * 100, y=df.hero_name, mode="text", showlegend=False,
                             text=[f"{v:.0f}%" for v in df.p1_contest_rate * 100], textposition="middle right",
                             textfont=dict(size=11, color=INK_2), hoverinfo="skip", cliponaxis=False))
    fig.update_layout(barmode="stack", bargap=0.25, legend=dict(traceorder="normal"),
                      title=_title(f"Who gets grabbed or denied first? First-phase priority, patch {patch}",
                                   f"Share of matches where the hero is picked or banned in phase 1 (draft slots 0-8: "
                                   f"7 bans, then 2 picks); top {n} heroes"),
                      xaxis=dict(title="Share of matches (%)", ticksuffix="%"),
                      yaxis=dict(title=None, showgrid=False), margin=dict(l=150, r=60, t=110, b=105))
    _save(fig, "draft_priority", height=720)


def synergy(con, n: int = 10) -> None:
    df = con.sql(f"""(SELECT * FROM hero_synergy WHERE patch_id IS NULL ORDER BY lift DESC LIMIT {n})
                     UNION ALL (SELECT * FROM hero_synergy WHERE patch_id IS NULL ORDER BY lift LIMIT {n})""").df()
    df = df.sort_values("lift")
    df["pair"] = df.hero_a_name + " + " + df.hero_b_name + "  (" + df.games.astype(str) + ")"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.expected_win_rate * 100, y=df.pair, mode="markers", name="expected (individual win rates)",
                             marker=dict(symbol="line-ns", size=14, line=dict(color=INK_2, width=2)),
                             hovertemplate="%{y}: expected %{x:.1f}%<extra></extra>"))
    for d, name, color in [(df[df.lift > 0], f"top {n} by lift", BLUE), (df[df.lift < 0], f"bottom {n} by lift", RED)]:
        fig.add_trace(go.Scatter(
            x=d.win_rate * 100, y=d.pair, mode="markers", name=f"{name}: observed win rate (95% CI)",
            marker=dict(color=color, size=10, line=dict(color=SURFACE, width=2)),
            error_x=dict(type="data", symmetric=False, array=(d.ci_high - d.win_rate) * 100,
                         arrayminus=(d.win_rate - d.ci_low) * 100, color=MUTED, thickness=1.5, width=0),
            customdata=d.lift * 100, hovertemplate="%{y}: %{x:.1f}% (lift %{customdata:+.1f} pp)<extra></extra>"))
    fig.add_hline(y=n - 0.5, line=dict(color=GRID, width=1))
    fig.add_vline(x=50, line=dict(color=MUTED, width=1, dash="dot"))
    fig.update_layout(title=_title(f"Best and worst same-team hero pairs, all patches pooled",
                                   "Pairs ranked by lift = observed - expected win rate; "
                                   "games together in brackets, at least 50"),
                      xaxis=dict(title="Win rate when both heroes are on the same team", ticksuffix="%"),
                      yaxis=dict(title=None, showgrid=False), margin=dict(l=280, r=40, t=110, b=105))
    _save(fig, "synergy", height=780)


def side_advantage(con) -> None:
    df = con.sql("SELECT * FROM side_advantage WHERE patch_id IS NOT NULL ORDER BY patch_id").df()
    pooled = con.sql("SELECT radiant_win_rate FROM side_advantage WHERE patch_id IS NULL").fetchall()[0][0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(df.patch_name) + list(df.patch_name[::-1]),
                             y=list(df.ci_high * 100) + list(df.ci_low[::-1] * 100), fill="toself", mode="lines",
                             fillcolor="rgba(42,120,214,0.15)", line=dict(width=0), name="95% CI (Wilson)",
                             hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df.patch_name, y=df.radiant_win_rate * 100, mode="lines+markers", name="Radiant win rate",
                             line=dict(color=BLUE, width=2), marker=dict(size=9, line=dict(color=SURFACE, width=2)),
                             customdata=df[["ci_low", "ci_high"]].values * 100, text=df.matches,
                             hovertemplate="%{x}: %{y:.1f}% (CI %{customdata[0]:.1f}-%{customdata[1]:.1f}%, "
                                           "%{text:,} matches)<extra></extra>"))
    fig.add_hline(y=50, line=dict(color=INK_2, width=1, dash="dash"))
    fig.add_hline(y=pooled * 100, line=dict(color=MUTED, width=1, dash="dot"))
    fig.add_annotation(x=1, xref="paper", y=pooled * 100, text=f"all patches: {pooled * 100:.1f}%", showarrow=False,
                       xanchor="right", yanchor="bottom", font=dict(size=11, color=MUTED))
    fig.add_annotation(x=1, xref="paper", y=50, text="no side advantage", showarrow=False,
                       xanchor="right", yanchor="top", font=dict(size=11, color=INK_2))
    fig.update_layout(title=_title("Does Radiant have the edge? Radiant win rate by patch",
                                   "Share of matches won by the Radiant side, with Wilson 95% confidence band"),
                      xaxis=dict(title="Patch", type="category", showgrid=False),
                      yaxis=dict(title="Radiant win rate", ticksuffix="%", range=[47, 56]))
    _save(fig, "side_advantage")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    FIG.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(DB, read_only=True) as con:
        contest_heatmap(con)
        winrate_scatter(con)
        diversity_line(con)
        risers_fallers(con)
        draft_priority(con)
        synergy(con)
        side_advantage(con)
