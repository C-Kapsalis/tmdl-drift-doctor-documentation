# Configuration file for the Sphinx documentation builder.
#
# Deliberately minimal: two extensions, the Read the Docs theme, nothing
# else. No autodoc, no napoleon, no custom directives - every page in this
# project is hand-written reStructuredText.

project = 'tmdl-drift-doctor'
copyright = '2026, Christoforos Kapsalis'
author = 'Christoforos Kapsalis'
release = '0.1.0'

extensions = [
    'sphinx.ext.intersphinx',
    'sphinxcontrib.spelling',
]

# One entry per sibling project. Uncomment each line once that project is
# live on Read the Docs, and confirm the slug matches its actual RTD
# project name.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'diataxis': ('https://diataxis.fr', None),
    # 'preflight': ('https://tmdl-preflight.readthedocs.io/en/latest/', None),
    # 'plot-styler': ('https://pbi-plot-styler.readthedocs.io/en/latest/', None),
    # 'model-forge': ('https://pbip-model-forge.readthedocs.io/en/latest/', None),
    # 'report-template': ('https://bi-report-template-site.readthedocs.io/en/latest/', None),
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

spelling_lang = 'en_US'

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
