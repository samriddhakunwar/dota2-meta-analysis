"""Dota 2 Pro Meta & Draft dashboard. Reads only the small aggregated tables in data/app/ (committed to git).
Entry point: page config, global patch selector, navigation and footer. Pages live in app/views/."""
import streamlit as st

st.set_page_config(page_title="Dota 2 Pro Meta & Draft Analysis", page_icon=":material/swords:", layout="wide")

import ui  # noqa: E402  (after set_page_config: registers the Plotly template)

nav = st.navigation([
    st.Page("views/meta_overview.py", title="Meta Overview", icon=":material/dashboard:", default=True),
    st.Page("views/hero_lookup.py", title="Hero Lookup", icon=":material/person_search:", url_path="hero-lookup"),
    st.Page("views/draft_priority.py", title="Draft Priority", icon=":material/gavel:", url_path="draft-priority"),
    st.Page("views/synergy_explorer.py", title="Synergy Explorer", icon=":material/group:",
            url_path="synergy-explorer"),
    st.Page("views/side_advantage.py", title="Side Advantage", icon=":material/balance:", url_path="side-advantage"),
])

with st.sidebar:
    names = ui.patch_names()
    # keyed widget in the entry script: rendered on every page, so the choice persists across pages
    st.selectbox("Patch", names[::-1], key="patch", help="Every page shows this patch unless it says otherwise.")
    total = ui.load("side_advantage").query("patch_name == 'All patches'").matches.iloc[0]
    with st.container(border=True):
        st.markdown(
            "**About this project**  \n"
            f"{total:,} Captains Mode pro matches (Jan 2024 – Sep 2026), analysed with SQL on DuckDB. "
            "Every win rate comes with a 95% confidence interval, so noise isn't sold as insight.  \n"
            f":material/code: [GitHub repo]({ui.GITHUB})  \n"
            f":material/dataset: [Kaggle dataset]({ui.DATASET})")

nav.run()

st.divider()
st.caption(
    f"Data: [Dota 2 Pro League Matches]({ui.DATASET}) by bwandowando on Kaggle (sourced from OpenDota) · "
    f"Built by Samriddha Kunwar · [GitHub]({ui.GITHUB}) · [LinkedIn]({ui.LINKEDIN}) · "
    "Not affiliated with Valve.")
