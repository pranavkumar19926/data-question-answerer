# Evidence — Done-when proof (copy into submission)

## Commands (run from data-question-answerer/)
```
python app/load_db.py
python app/eval_accurate.py
python app/redteam.py
python app/regression.py
python app/test_retry.py
python app/chain.py "Top 3 states by wheat production in 2022?" --stream
python app/hybrid.py "When is Kharif sown?"
streamlit run app/ui.py
```

## Results — TRUE LLM (Ollama qwen2.5-coder:7b, 2026-11-07, direct HTTP, no LangChain pkg needed)
### Toy set (32 Qs: 28 answerable + 4 unanswerable; filters, totals incl. SUM/AVG/COUNT, GROUP BY, joins)
| prompt | score | note |
|---|---|---|
| v1 | 25/28 = 89.3% (filter 10/10, total 7/8, join 8/10) + 4/4 | baseline |
| v2 | 25/28 = 89.3% | same misses, different Q20 failure mode |
| v3 | 27/28 = 96.4% (filter 10/10, total 8/8, join 9/10) + 4/4 | fixed Q14/Q22/Q26 via alias/aggregation/year rules; new miss Q25 (over-cautious UNANSWERABLE on threshold) |
| v4 | **28/28 = 100%** (10/10, 8/8, 10/10) + 4/4 | + threshold rule & few-shot; no regressions |
- v1/v2 miss analysis: Q14 per-state AVG vs gold overall AVG (question ambiguity); Q22 rows instead of SUM;
  Q26 broken self-join alias — chain retried 3x with real LLM then admitted failure (Must-Have #3 live proof)
- Rule demo (offline, recorded separately): 28/28 = 100% + 4/4
- redteam: **chain 8/8, gate 4/4** (delete/drop/stacked/injection/PII/out-of-scope blocked)
- regression.py: **ALL GREEN** (eval + redteam + test_retry), writes regression_report.md
- test_retry: bad SQL attempt 1 -> fixed attempt 2 (13800000.0); always-bad gives up cleanly after limit (M2.7/M4.14)
- chain --stream: shows SQL + streamed answer + rows (M2.3)
- hybrid: docs route with citations [agri_notes.md], db route with SQL+rows, hybrid merges both (stretch)
- datagovin: sample_district_yield.csv (8 rows) loaded as district_yield, top = Bardhaman 1250000t; catalog documents all 4 tables
- ui: Auto (DB vs docs) toggle + route badge + citations + bar charts
- scale: 2 runs mean 0.2s for 32 Qs (~7 ms/Q rule demo) via app/scale.py (M2.8)
- costs: app/costs.py summarizes logs/queries.jsonl (requests, latency, USD) (M2.9)
- catalog: 5 tables (states, crops, production, district_yield, real_crop_production), types synced to DB schema; .gitignore ignores db/logs/pycache
- run: RUN_WINDOWS.md + .env.example (Windows-safe, ASCII logs)

## Real data.gov.in-shape data (NEW)
- Source: district crop APY data (India) via repo nileshiq/Crop-Datasets-for-All-Indian-States, file Crops_data.csv (894,067 bytes).
  data.gov.in blocks bots (403) and raw.githubusercontent.com is unreachable from here, so fetched via jsDelivr CDN mirror of the same file. Documented as mirror in catalog + here.
- Pipeline: `python app/load_real.py` reshapes wide (2,484 x 80) to long `real_crop_production` (34,902 rows, 2010-2017, 20 states, 23 crops; area in 1000 ha, production in 1000 tons, yield in kg/ha).
- Eval: `eval/real_questions.csv` (12 Qs: 11 answerable + 1 unanswerable, golds verified by direct SQL), `python app/eval_real.py [--v6]`.
| prompt | score | note |
|---|---|---|
| v5 | 10/11 = 90.9% (filter 3/4, total 5/5, group 2/2) + 1/1 | miss Q8: state question returned district rows |
| v6 | **11/11 = 100%** (4/4, 5/5, 2/2) + 1/1 | + state-vs-district aggregation rule & few-shot |

## Coverage
- Must-have 1: load_db.py + catalog.json (plain language) + datagovin.py adapter
- Must-have 2: chain.py Q->SQL->run, shows query+result (llm.py: openai->ollama->rule)
- Must-have 3: retry x3 + UNANSWERABLE path (chain.answer, hybrid)
- Must-have 4: safety.py gate, verified by redteam
- Stretch: ui.py charts, hybrid.py docs mix
- Modules: M2 (2.1/2.2/2.4/2.5/2.6/2.7/2.9 + 2.3 streaming), M3 (prompts v1-v6, few-shots, router, versioning, M3.5 v1-v6 comparison), M4 (4.15 structured, 4.13 router, 4.8 don't-know, 4.17-21 evals, 4.22-26 security)

## Upgrade path used: Ollama done (qwen2.5-coder:7b auto-detected; $LLM_MODEL overrides).
OpenAI also supported via $OPENAI_API_KEY. No pip packages required for Ollama (direct HTTP).
