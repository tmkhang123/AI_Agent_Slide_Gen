# AI Slide Agent Maker

## Project Overview

This project creates Vietnamese PowerPoint decks from a user topic using a
three-agent pipeline:

1. `PlannerAgent` receives the topic and creates the slide outline.
2. `ContentAgent` writes detailed bullet content for each planned slide.
3. `DesignerAgent` builds the final `.pptx`, optionally adding background
   images and managing output versioning.

The current production flow is:

```text
topic -> PlannerAgent -> ContentAgent -> DesignerAgent -> .pptx
```

`SlidesMakerOrchestrator` in `orchestrator.py` coordinates the pipeline and
saves intermediate JSON files into `Product/`.

## Key Files

- `main.py`: CLI entry point. Supports topic input and rebuilding from
  `*_content.json`.
- `orchestrator.py`: pipeline coordinator for the three agents.
- `schema.py`: shared data contracts between agents (`Outline`, `SlideBrief`,
  `Deck`, `Slide`).
- `agent_planner.py`: Agent 1, creates the outline and image search queries.
- `agent_content.py`: Agent 2, generates slide content one slide at a time.
- `agent_designer.py`: Agent 3, creates the PowerPoint deck.
- `llm.py`: Ollama client plus tolerant text parsers.
- `slide_generator.py`: PowerPoint layout and rendering with `python-pptx`.
- `image_fetcher.py`: DuckDuckGo image fetcher with placeholder fallback.
- `gui_app.py`: Streamlit GUI.
- `watcher.py`: watches edited `*_content.json` files and rebuilds the deck.
- `selftest.py`: offline test for parsers and fallback pipeline.

Older files such as `ai_engine.py` are legacy helpers and are not the main
three-agent implementation.

## Run Commands

```powershell
# Create environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# CLI full pipeline
.\.venv\Scripts\python.exe main.py "Lợi ích của AI trong giáo dục"

# Rebuild PPTX from edited content JSON
.\.venv\Scripts\python.exe main.py Product\<name>_content.json

# GUI
.\.venv\Scripts\python.exe -m streamlit run gui_app.py

# Watch mode
.\.venv\Scripts\python.exe watcher.py

# Offline structural test
.\.venv\Scripts\python.exe selftest.py
```

## LLM Notes

The default model is Ollama `llama3.1:8b` at `http://localhost:11434`.
The new implementation intentionally avoids forcing one large JSON response.
Planner and Content ask for plain text, then `llm.py` parses the output
tolerantly. This prevents the common failure where the model returns only one
slide or malformed JSON.

## Repository Hygiene

Do not commit generated or local environment files:

- `.venv/`
- `__pycache__/`
- `Product/`
- `*.pptx`
- `.env`

