# AI Support Ticket Analyst

A Python-only AI system for querying customer-support tickets and detecting operational anomalies.

## Features

- Loads `data/support_tickets.csv` into Pandas.
- Uses an LLM through Ollama to translate natural-language questions into structured JSON.
- Executes calculations with Pandas for reliable numeric results.
- Detects unresolved High/Critical tickets and unusually long resolution times.
- Exposes FastAPI endpoints and a Streamlit UI.

## Architecture

`User question -> FastAPI -> Ollama LLM -> structured query JSON -> Pandas -> response`

The LLM interprets intent; Pandas performs the actual filtering, grouping, and aggregation. This reduces hallucinated numbers.

## Setup

1. Install Python 3.10+.
2. Create and activate a virtual environment:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install Ollama and pull a free local model:

```bash
ollama pull llama3.2:3b
```

5. Start the API:

```bash
uvicorn main:app --reload
```

6. In a second terminal, start the UI:

```bash
streamlit run app.py
```

Open the Streamlit URL shown in the terminal.

## API endpoints

- `GET /health`
- `POST /query` with JSON body `{ "question": "How many tickets are currently open?" }`
- `GET /anomalies`

Swagger documentation is available at `/docs`.

## Example questions

- How many tickets are currently open?
- Which agent resolved the most tickets?
- What is the average customer rating for Technical category tickets?
- Show all Critical tickets that are not resolved.
- Group tickets by category.

## Known limitations

- The dataset is static unless `DATA_PATH` is changed.
- The current anomaly rule flags unresolved High/Critical tickets and resolution times above the 95th percentile.
- Ollama must be running for true LLM interpretation. A small heuristic fallback is included so the API remains demonstrable if Ollama is unavailable.
- Date phrases such as “this month” require extending the query schema with explicit date filters.

## Submission checklist

- Push all files to GitHub.
- Confirm `uvicorn main:app` starts successfully.
- Confirm `/docs`, `/query`, `/anomalies`, and Streamlit work.
- Email the repository link with subject: `[AI Engineer Assessment] — Pavani Sriya`.
