from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _names(specs: list[str]) -> set[str]:
    return {re.split(r"[\[<>=!~ ;]", spec, maxsplit=1)[0].lower() for spec in specs}


def test_streamlit_requirements_are_declared_in_pyproject() -> None:
    """The deployed demo installs requirements.txt, so nothing in it may drift from pyproject."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    declared = _names(project["dependencies"]) | _names(project["optional-dependencies"]["demo"])

    lines = (ROOT / "requirements.txt").read_text().splitlines()
    listed = _names([ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")])

    assert listed <= declared
    assert {"streamlit", "pymupdf", "google-genai", "pydantic"} <= listed
