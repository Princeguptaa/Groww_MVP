"""Streamlit Cloud default entry point."""
from pathlib import Path
import runpy

app_path = Path(__file__).resolve().parent / "app.py"
runpy.run_path(str(app_path), run_name="__main__")
