# SIP Pause Guide

A small web tool for first-time SIP investors who are thinking about pausing or stopping.
It helps users understand their lighter options — skip, reduce, or a longer break — before stopping a SIP.

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

## Run evaluation

The evaluation script runs the AI router (with defensive gates) and the rule baseline on the golden set:

```bash
# Set GEMINI_API_KEY in your environment
export GEMINI_API_KEY="your-key-here"  # On Windows PowerShell: $env:GEMINI_API_KEY="your-key-here"

# Run evaluation (uses eval/golden_set.csv or falls back to eval/golden_set_demo.csv)
python eval/run_eval.py
```

The script writes `eval/results.json`, which governs whether AI routing is turned ON in the application.

## Run tests

```bash
pytest tests/ -v
```

## How it works

1. **Step 1: Tell us what is going on** — The user describes what is going on in English or Hinglish (or taps one of six chips).
2. **Step 2: What we understood** — A classifier (AI or rule-based fallback) categorises the reason into one of six standard codes and quotes verbatim evidence back to the user.
3. **Step 3: Your options** — Shows reason-specific guidance, followed by all four option cards ("Skip this month", "Reduce the amount for a while", "Take a longer break", "Stop the SIP") with official Groww Help steps and links.
4. **Calendar reminder** — If the user selects Skip or Take a longer break, an optional `.ics` calendar reminder can be downloaded to check back on their plan in two months.

## Architecture and Hard Rules

- **No Investment Advice:** The tool does not rank, recommend, or compare funds, stocks, or financial schemes.
- **No Fear or FOMO:** Neutral, factual wording only. No countdowns, guilt wording, or loss-framing.
- **Equal Prominence:** The "Stop the SIP" option is always visible and has the same visual weight as the lighter options.
- **Privacy First:** Messages are treated strictly as data and are never stored or logged to disk or databases.
- **Deterministic Fixed Content:** All advice explanations, steps, and consequence descriptions are human-written from official Groww Help documentation. The AI only classifies reasons and extracts the verbatim quote.

Not investment advice. Does not store messages or personal data.
