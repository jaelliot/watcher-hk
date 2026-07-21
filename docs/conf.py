"""Sphinx configuration for the Watopnet documentation."""

from __future__ import annotations

import os

try:
    import sphinx_rtd_theme
except ImportError:
    sphinx_rtd_theme = None

# Project information

project = "Watopnet"
author = "KERI Foundation"
copyright = "2024 - 2026, KERI Foundation and contributors"
version = release = "0.0.1"

# General configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_mock_imports = [
    "falcon",
    "hio",
    "keri",
    "multicommand",
    "ordered_set",
    "pyotp",
]
napoleon_include_init_with_doc = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output

if sphinx_rtd_theme:
    html_theme = "sphinx_rtd_theme"
else:
    html_theme = "alabaster"

STATIC_DIR = os.path.join(os.path.dirname(__file__), "_static")

if os.path.isdir(STATIC_DIR):
    html_static_path = ["_static"]
