# BizScopeAI frontend

The local app has two frontend entry points:

- `app.py` is the legacy Streamlit interface.
- `web/index.html` is the current single-page chat interface served by the
  FastAPI app.

The web interface keeps its source organized by asset type:

```text
frontend/
├── app.py
└── web/
    ├── index.html
    ├── favicon.ico
    └── assets/
        ├── favicon.svg
        ├── css/styles.css
        └── js/app.js
```

The web UI uses native browser JavaScript modules and CSS. It does not need a
Node, npm, React, or bundler installation. FastAPI serves `web/` as its static
root, so the asset URLs in `web/index.html` are `/assets/css/styles.css` and
`/assets/js/app.js`.
