# Windows run guide (PowerShell)

## 1) First run (no keys needed)
```powershell
cd data-question-answerer
python app/load_db.py
python app/eval_accurate.py
python app/redteam.py
python app/chain.py "Top 3 states by wheat production in 2022?" --stream
```

## 2) UI
```powershell
pip install -r requirements.txt
streamlit run app/ui.py
```

## 3) Real LLM (pick one)
```powershell
# OpenAI
$env:OPENAI_API_KEY="sk-..."
python app/eval_accurate.py        # v2
python app/eval_accurate.py --v1  # compare
# Ollama (free local, no pip packages needed — direct HTTP to localhost:11434)
ollama serve
ollama pull llama3.1:8b   # or keep any model you have; auto-detected
$env:LLM_MODEL="qwen2.5-coder:7b" # optional: force a specific pulled model
python app/chain.py "Total soybean production in 2022?"
```

## 4) Real CSV
```powershell
Copy-Item your.csv data/raw/
python app/datagovin.py data/raw/your.csv --table mytable
# then edit app/catalog.json meanings + add eval rows
```

## 5) Proof
```powershell
python app/regression.py   # writes regression_report.md
python app/scale.py --runs 3
python app/costs.py
```
Notes: repo prints ASCII only (cp1252-safe). DB opens read-only (`mode=ro`).
