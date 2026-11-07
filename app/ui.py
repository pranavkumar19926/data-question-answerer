"""Streamlit UI — stretch goal: charts + show query+result.
Run: streamlit run app/ui.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import streamlit as st
import pandas as pd
from chain import answer
from hybrid import hybrid_answer

st.set_page_config(page_title="Data Question Answerer", layout="wide")
st.title("Data Question Answerer (Modules 2+3+4)")
st.caption("Ask plain-English questions. Shows SQL + result + figures. Read-only, LIMIT 100.")

mode = st.radio("Answer from:", ["Auto (DB vs docs)", "Database only"], horizontal=True)
examples = ["Production of rice in Punjab in 2022?",
            "Top 3 states by wheat production in 2022?",
            "When is Kharif sown?",
            "What is yield and which year data do we have?"]
docs_examples = ["When is Kharif sown?", "What is yield and which year data do we have?"]
q = st.text_input("Your question", value=examples[1])
col1, col2 = st.columns([1, 3])
if col1.button("Ask") or q:
    with st.spinner("Writing + running SQL..."):
        out = hybrid_answer(q) if mode.startswith("Auto") else {"route": "db", **answer(q)}
    st.caption(f"Route: {out.get('route')} | Attempts: {out.get('attempts', 1)} | read-only, max 100 rows")
    if out.get("sql"):
        col2.code(out.get("sql", ""), language="sql")
    st.write(out["answer"])
    if out.get("citations"):
        st.caption("Sources: " + ", ".join(out["citations"]))
    rows = out.get("rows", [])
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, hide_index=True, width="stretch")
        # Chart stretch goal: bar chart when GROUP BY shape detected
        if len(df.columns) >= 2 and pd.api.types.is_numeric_dtype(df[df.columns[1]]):
            try:
                st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])
            except Exception:
                pass
st.divider()
st.markdown("**Try:** " + " | ".join(examples))
