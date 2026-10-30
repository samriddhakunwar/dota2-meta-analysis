"""Shared look for every page: palette, Plotly template, data loading, table formats and small UI helpers."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "app"

# palette (matches .streamlit/config.toml); data colours validated for colour-blind separation on SURFACE
BG, SURFACE, INK, INK_2, GRID = "#0b0f17", "#141a24", "#e6e8ec", "#9aa3b2", "#262e3b"
ACCENT = "#e5484d"  # UI chrome only, never a data colour
BLUE, ORANGE, GRAY = "#3987e5", "#d95926", "#666b75"
# one colour per verdict, on every page: "better than expected" blue, "worse" orange, noise gray
LABEL_COLORS = {"overperformer": BLUE, "synergy": BLUE, "trap pick": ORANGE, "anti-synergy": ORANGE,
                "within noise": GRAY}
LABEL_ICONS = {"overperformer": "🔵", "synergy": "🔵", "trap pick": "🟠", "anti-synergy": "🟠"}

GITHUB = "https://github.com/samriddhakunwar/dota2-meta-analysis"
DATASET = "https://www.kaggle.com/datasets/bwandowando/dota-2-pro-league-matches-2023"
LINKEDIN = "https://www.linkedin.com/in/your-profile"  # TODO: replace with your LinkedIn URL

_axis = dict(gridcolor=GRID, linecolor=GRID, zeroline=False, automargin=True, title_font=dict(color=INK_2, size=13),
             tickfont=dict(color=INK_2))
pio.templates["dota_dark"] = go.layout.Template(layout=dict(
    font=dict(family="Source Sans Pro, Segoe UI, Helvetica, Arial, sans-serif", size=13, color=INK_2),
    title=dict(font=dict(size=16, color=INK), x=0, xanchor="left"),
    paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, colorway=[BLUE, ORANGE, GRAY],
    xaxis=_axis, yaxis=_axis,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, xanchor="left", title_text="",
                bgcolor="rgba(0,0,0,0)", font=dict(color=INK)),
    hoverlabel=dict(bgcolor=BG, bordercolor=GRID, font=dict(color=INK, size=13)),
    margin=dict(l=12, r=16, t=48, b=12),
))
pio.templates.default = "dota_dark"


@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA / f"{name}.parquet")


def pct(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Rates as percentages, for display."""
    return df.assign(**{c: df[c] * 100 for c in cols})


def patch_names() -> list[str]:
    return load("patches").query("included").sort_values("patch_id").patch_name.tolist()


def patch() -> str:
    """The globally selected patch (sidebar widget, kept in session_state)."""
    return st.session_state.get("patch") or patch_names()[-1]


def verdict(labels: pd.Series) -> pd.Series:
    return labels.map(lambda s: f"{LABEL_ICONS.get(s, '')} {s}".strip() if isinstance(s, str) else "under 100 picks")


# table column formats: values are already ×100 via pct(); compact widths so tables fit narrow screens
def PCT(label: str, help: str | None = None):
    return st.column_config.NumberColumn(label, format="%.1f%%", help=help, width="small")


def BAR(label: str, max_value: float = 100, help: str | None = None):
    return st.column_config.ProgressColumn(label, format="%.1f%%", min_value=0, max_value=max_value, help=help,
                                          width="small")


def INT(label: str, help: str | None = None):
    return st.column_config.NumberColumn(label, format="localized", help=help, width="small")


TEXT = st.column_config.TextColumn


def header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def explain(text: str) -> None:
    with st.expander("How to read this", icon=":material/help:"):
        st.markdown(text)


def chart(fig: go.Figure, height: int = 460, title: str | None = None) -> None:
    if title:  # title outside the figure, so a wrapping legend can never overlap it on narrow screens
        st.markdown(f"**{title}**")
    fig.update_layout(height=height)
    # theme=None: use our template instead of Streamlit's override
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def ci_text(lo: float, hi: float) -> str:
    return f"95% CI {lo:.1%}–{hi:.1%}"
