"""Upload any CSV, ask questions, get SQL + table + bar chart. Run: streamlit run app/upload_app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from anydata import ask_any, load_upload, pick_chart

st.set_page_config(page_title="Ask your data", layout="wide")
st.title("Ask your data")
st.caption("Upload a CSV, ask in plain words, get the SQL, the rows, and a chart. Read-only, max 100 rows.")

for key, default in {"table": None, "catalog": None, "info": None, "result": None,
                     "question": "What are the top 5 rows by the first numeric column?"}.items():
    st.session_state.setdefault(key, default)

with st.container(border=True):
    st.subheader("Step 1 · Upload a CSV file")
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"], label_visibility="collapsed")
    if uploaded is not None:
        raw = uploaded.getvalue()
        cache_key = (uploaded.name, len(raw))
        if st.session_state.get("upload_key") != cache_key:
            with st.spinner("Loading file into a read-only database..."):
                info = load_upload(raw, uploaded.name)
            st.session_state.update(table=info["table"], catalog=info["catalog"],
                                    info=info, result=None, upload_key=cache_key)
        info = st.session_state["info"]
        st.success(f"Loaded {info['rows']} rows × {len(info['cols'])} columns as table `{info['table']}`.")
        st.dataframe(pd.DataFrame(info["preview"]), hide_index=True,
                     alt="First five rows of the uploaded file")

if st.session_state["table"] is None:
    st.info("Upload a CSV above to start. Try the sample: data/raw/sample_district_yield.csv.")
    st.stop()

with st.container(border=True):
    st.subheader("Step 2 · Ask a question")
    with st.form("ask_form"):
        q = st.text_input("Question about your file", value=st.session_state["question"])
        submitted = st.form_submit_button("Ask", width="stretch")
    if submitted and q.strip():
        st.session_state["question"] = q
        with st.spinner("Writing and running SQL..."):
            st.session_state["result"] = ask_any(q, st.session_state["table"], st.session_state["catalog"])

result = st.session_state["result"]
if result is None:
    st.stop()

with st.container(border=True):
    st.subheader("Step 3 · Answer")
    st.write(result["answer"])
    if result.get("sql"):
        st.code(result["sql"], language="sql")
    rows = result.get("rows", [])
    if not rows:
        st.stop()
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, alt="Query result rows")
    picked = pick_chart(df)
    if picked is not None:
        x, y = picked
        st.bar_chart(df, x=x, y=y, alt=f"Bar chart of {y} by {x} for the asked question")
    st.caption(f"Source: {result.get('source')} · attempts: {result.get('attempts')} · read-only, max 100 rows")
