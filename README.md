# SIP Pause Guide

A small web tool for first-time SIP investors who are thinking about pausing or stopping.
It helps users understand their lighter options — skip, reduce, or pause — before stopping a SIP.

**Prototype for research. Not investment advice.**

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Set your Gemini API key in `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-key-here"
```

## Run tests

```bash
pytest tests/ -v
```

## How it works

1. The user describes what is going on (free text or tap chips).
2. A router (AI or keyword-based) picks the most likely reason.
3. The tool shows fixed, human-written explanations and all four options with Groww Help steps.
4. The user decides. Nothing is blocked, nothing is automatic.

Not investment advice. Does not store messages or personal data.

