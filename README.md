# Data Question Answerer 🗣️➡️🗃️

Ask plain-English questions about your data. Get back the **SQL**, the **answer with figures**, and a **bar chart** — powered by a local LLM, with a read-only safety gate on every query.

Built as a course project covering **Text-to-SQL, safe tool calling, prompt engineering (v1→v6), and RAG-style evaluation** — verified end-to-end with **44 test questions at 100% accuracy**.

## ✨ What it does

| You do | You get |
|---|---|
| Upload **any CSV** (or use the built-in Indian crop datasets) | A read-only database table + plain-language column catalog |
| Ask, e.g. *"Top 3 states by wheat production in 2022?"* | The SQL it wrote, the result rows, and a bar chart |
| Ask something unanswerable or dangerous | *"I can't answer this from the data"* — writes are blocked, never executed |

Two interfaces:
- **Upload app** (`app/upload_app.py`) — upload any CSV → ask → SQL + table + chart
- **CLI + curated datasets** (`app/chain.py`) — toy agriculture DB, real district-level data (34,902 rows), docs-hybrid answers

## 🚀 Quickstart (Windows, 5 minutes)

**1. Prerequisites:** [Python 3.12+](https://www.python.org/downloads/) and [Ollama](https://ollama.com/download) (free, runs models on your laptop — no API keys, no cloud costs).

**2. Get the code and enter the folder:**
```powershell
git clone https://github.com/pranavkumar19926/data-question-answerer.git
cd data-question-answerer
```

**3. Start the local model** (separate window, leave it open):
```powershell
ollama serve
ollama pull qwen2.5-coder:7b
```

**4. Build the databases** (runs once):
```powershell
python app/load_db.py     # toy agriculture DB (states × crops × production)
python app/load_real.py    # real district-level data, 2010–2017 (34,902 rows)
```

**5a. Ask from the terminal:**
```powershell
python app/chain.py "Top 3 states by wheat production in 2022?" --stream
python app/chain.py --real "Compare rice production in Punjab 2016 vs 2017 (1000 tonnes)?" --stream
```

**5b. Or use the web apps:**
```powershell
pip install -r requirements.txt
streamlit run app/upload_app.py   # upload any CSV → SQL + table + chart
streamlit run app/ui.py           # curated-dataset explorer
```

## 🧠 How it works

```
Your question
  │  (prompt v4/v6: schema + hard rules + few-shots)
  ▼
Local LLM writes ONE SQLite query (structured {"sql": ...} output)
  │  (safety gate: SELECT-only, read-only connection, auto LIMIT 100)
  ▼
Run → Retry up to 3× on error → or admit "can't answer"
  │
  ▼
Answer with figures + SQL + table + bar chart
```

Key engineering decisions:
- **Safety first**: the model can only ever produce `SELECT`. The gate blocks `INSERT/UPDATE/DELETE/DROP`, stacked statements, and caps rows — verified by a 12-case red-team suite.
- **Prompts are versioned** (`app/prompts/v1_sql.txt` → `v6_sql.txt`). Every version is scored on the same eval sets, so improvements are measured, not vibes.
- **Every failure mode found became a rule**: invented table aliases → alias whitelist; rows-instead-of-SUM → aggregation rules; self-joins → `IN + ORDER BY` pattern; state-vs-district confusion → grain rule.

## 📊 Measured accuracy (local `qwen2.5-coder:7b`, no API)

**Toy set — 32 questions** (filters, SUM/AVG/COUNT totals, GROUP BY, JOINs, 4 unanswerable):

| Prompt | Accuracy |
|---|---|
| v1 / v2 | 89.3% (25/28) |
| v3 (alias + aggregation + year rules) | 96.4% (27/28) |
| **v4** (+ threshold rule & few-shot) | **100% (28/28)** + 4/4 unanswerable |

**Real district data — 12 questions** (all golds verified by direct SQL):

| Prompt | Accuracy |
|---|---|
| v5 | 90.9% (10/11) |
| **v6** (+ state-vs-district grain rule) | **100% (11/11)** + 1/1 unanswerable |

Reproduce: `python app/eval_accurate.py --v4` · `python app/eval_real.py --v6` · `python app/redteam.py` · `python app/regression.py`

## 📁 Project structure

```
data-question-answerer/
├── app/
│   ├── chain.py          # question → SQL → run → explain (CLI, --stream, --real, --v1..v6)
│   ├── llm.py            # OpenAI → Ollama (direct HTTP, no LangChain needed) → rule fallback
│   ├── safety.py         # read-only SQL gate
│   ├── anydata.py        # upload-any-CSV engine: load, auto-catalog, generic prompt, ask
│   ├── upload_app.py     # Streamlit: upload → ask → SQL + table + bar chart
│   ├── ui.py             # Streamlit explorer for the curated datasets
│   ├── hybrid.py         # DB-vs-docs router with citations (RAG stretch goal)
│   ├── load_db.py        # builds the toy SQLite DB
│   ├── load_real.py      # reshapes the real wide CSV into a long tidy table
│   ├── datagovin.py      # load any data.gov.in-style CSV + catalog stub
│   ├── eval_accurate.py  # gold-value eval with per-type breakdown (toy set)
│   ├── eval_real.py      # gold-value eval (real set) · test_retry.py · redteam.py
│   └── prompts/          # versioned system prompts v1_sql.txt … v6_sql.txt
├── data/
│   ├── raw/              # Crops_data.csv (real, 894 KB) + small samples
│   └── docs/             # related notes for docs-hybrid answers
├── eval/                 # questions.csv (32) + real_questions.csv (12), golds DB-verified
└── logs/                 # per-request log: SQL, latency, est. cost (git-ignored)
```

## 📚 Data

- **Toy DB**: hand-built Indian agriculture demo (6 states × 5 crops × 2021–2022) — great for learning JOINs/aggregations.
- **Real DB** (`real_crop_production`): district-level Area–Production–Yield data for India, 2010–2017, 20 states, 23 crops, 34,902 rows (data.gov.in-shaped source; fetched via CDN mirror since data.gov.in blocks bots — see `EVIDENCE.md`).
- **Upload your own**: any CSV works through `upload_app.py` — columns are auto-described with sample values.

## 🛠️ Tech stack

Python · SQLite (read-only `mode=ro`) · Streamlit · Ollama (`qwen2.5-coder:7b`, direct HTTP API) · pandas · optional OpenAI (`gpt-4o-mini`) via `$OPENAI_API_KEY`

Course map: LangChain-style chaining & tool calling → prompt engineering & versioning → RAG patterns (router, citations, evals, red-teaming). Full mapping in `EVIDENCE.md`.

---
*Course project — Data Question Answerer (Intermediate, Modules 2+3+4). Prompts v1→v6 and all 44 eval golds are in this repo; every number above is reproducible with the commands shown.*
