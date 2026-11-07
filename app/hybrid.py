"""Keyword docs RAG (no embeddings needed) + DB-vs-docs router — M4.13 stretch.
- docs_rag(question): returns top passages from data/docs/*.md by keyword overlap, with citations.
- route(question): 'db' | 'docs' | 'hybrid' via simple rules (LLM router when key present).
Run: python app/hybrid.py "When is Kharif sown?"
"""
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

DOCS = list((Path(__file__).parent.parent / "data" / "docs").glob("*.md"))

def passages():
    out = []
    for d in DOCS:
        text = d.read_text(encoding="utf-8")
        # split on headings
        parts = re.split(r"\n##+\s+", text)
        for p in parts:
            p = p.strip()
            if len(p) > 40:
                out.append({"source": f"{d.name}", "text": p[:800]})
    return out

def docs_rag(question: str, k: int = 2):
    qs = set(re.findall(r"[a-z]+", question.lower()))
    scored = []
    for p in passages():
        ps = set(re.findall(r"[a-z]+", p["text"].lower()))
        score = len(qs & ps)
        scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for s, p in scored[:k] if s > 0]

DB_HINTS = ["production", "tonnes", "top", "total", "average", "how many",
            "punjab", "maharashtra", "bengal", "tamil", "uttar", "madhya",
            "rice", "wheat", "sugarcane", "cotton", "soybean", "2021", "2022", "yield"]
DOC_HINTS = ["when", "what is kharif", "what is rabi", "what is yield", "sown", "harvest",
             "season", "monsoon", "read production", "how to read", "notes", "which year",
             "years covered", "what is"]

def route(question: str) -> str:
    q = question.lower()
    db = sum(1 for h in DB_HINTS if h in q)
    dc = sum(1 for h in DOC_HINTS if h in q)
    if db > 0 and dc > 0:
        return "hybrid"
    if dc > db:
        return "docs"
    if db > 0:
        return "db"
    return "docs"  # default: admit via docs or unanswerable

def hybrid_answer(question: str):
    from chain import answer as db_answer
    r = route(question)
    if r == "db":
        out = db_answer(question)
        return {"route": r, **out}
    hits = docs_rag(question)
    if not hits:
        return {"route": r, "answer": "I can't answer this from the data or docs.",
                "sql": "UNANSWERABLE", "rows": [], "citations": []}
    if r == "docs":
        txt = " ".join(h["text"] for h in hits)[:600]
        return {"route": r, "answer": f"From docs: {txt}",
                "sql": "", "rows": [], "citations": [h["source"] for h in hits]}
    # hybrid: DB answer + docs context
    out = db_answer(question)
    ctx = " | ".join(h["text"][:200] for h in hits)
    out["answer"] += f" Docs add: {ctx}"
    out["citations"] = [h["source"] for h in hits]
    out["route"] = r
    return out

if __name__ == "__main__":
    import json
    q = " ".join(sys.argv[1:]) or "When is Kharif sown?"
    print(json.dumps(hybrid_answer(q), indent=2, default=str))
