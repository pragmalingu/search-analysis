"""Sphinx configuration."""
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.abspath('../src'))

project = "Search_Analysis"
author = "PragmaLingu"
copyright = f"{datetime.now().year}, {author}"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_click",
    "sphinx_rtd_theme",
]
autodoc_typehints = "description"
html_theme = "sphinx_rtd_theme"
