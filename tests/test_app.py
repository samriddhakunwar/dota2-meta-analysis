"""Smoke test: every dashboard page renders without exceptions for two patches (reads data/app/ only)."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGES = ["views/meta_overview.py", "views/hero_lookup.py", "views/draft_priority.py", "views/synergy_explorer.py",
         "views/side_advantage.py"]


@pytest.mark.parametrize("patch", ["7.41", "7.36"])
@pytest.mark.parametrize("page", PAGES)
def test_page_renders(page, patch):
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.selectbox(key="patch").set_value(patch).run()
    at.switch_page(page).run()
    assert not at.exception, at.exception
    assert at.title and at.dataframe  # the page actually rendered content
    assert at.selectbox(key="patch").value == patch  # global patch survives the page switch
    if page.endswith("synergy_explorer.py"):
        for pooled in (True, False):
            at.toggle[0].set_value(pooled).run()
            assert not at.exception, at.exception
