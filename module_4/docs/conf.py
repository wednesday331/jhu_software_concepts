import os
import sys

# Make the Module 4 source files importable by Sphinx.
sys.path.insert(
    0,
    os.path.abspath("../src"),
)

project = "GradCafe Analytics"
copyright = "2026, Shrey Shanbhag"
author = "Shrey Shanbhag"
release = "1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

html_theme = "sphinx_rtd_theme"

html_static_path = ["_static"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}