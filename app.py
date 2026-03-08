"""
RAG Chat Application - ChatGPT-like interface backed by ChromaDB + OpenAI.
Features: Chat with streaming, File-in-chat reference lookup, Document Upload, Library Review.
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import os, json, logging, re, tempfile, shutil
from pathlib import Path
from openai import OpenAI
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import chromadb

# ── Env loading ───────────────────────────────────────────────────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    with open(_env_path, "rb") as _f:
        for _line in _f.read().split(b"\n"):
            _line = _line.rstrip(b"\r").decode("utf-8", errors="ignore").strip()
            if "=" in _line and not _line.startswith('SNOWFLAKE_PRIVATE_KEY"') and not _line.startswith("#"):
                _k, _, _v = _line.partition("=")
                _k = _k.strip(); _v = _v.strip().strip('"')
                if _k and _k == _k.upper() and not os.environ.get(_k):
                    os.environ[_k] = _v

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# ── ChromaDB (lazy init so empty API key doesn't crash on startup) ─────────────
CHROMA_PATH     = Path(os.getenv("CHROMA_PATH", str(Path(__file__).parent / "chroma_db")))
COLLECTION_NAME = "rag_docs"
CHROMA_PATH.mkdir(parents=True, exist_ok=True)

_chroma: chromadb.PersistentClient | None = None
_collection = None

def get_collection():
    global _chroma, _collection
    if _chroma is None:
        _chroma = chromadb.PersistentClient(path=str(CHROMA_PATH))
    if _collection is None:
        api_key = os.getenv("OPENAI_API_KEY", OPENAI_API_KEY)
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Add it in Render > Environment.")
        ef = OpenAIEmbeddingFunction(api_key=api_key, model_name="text-embedding-3-small")
        _collection = _chroma.get_or_create_collection(
            name=COLLECTION_NAME, embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection

def retrieve_context(query: str, top_k: int = 8):
    col = get_collection()
    n   = min(top_k, col.count() or 1)
    res = col.query(query_texts=[query], n_results=n,
                    include=["documents", "metadatas", "distances"])
    out = []
    for cid, doc, meta, dist in zip(res["ids"][0], res["documents"][0],
                                     res["metadatas"][0], res["distances"][0]):
        out.append({
            "id":             cid,
            "text":           doc,
            "similarity":     round(1.0 - dist, 4),
            "source_file":    meta.get("source_file", ""),
            "title":          meta.get("title", ""),
            "authors":        meta.get("authors", ""),
            "published":      meta.get("published", ""),
            "doi":            meta.get("doi", ""),
            "page_reference": meta.get("page_reference", ""),
            "summary":        meta.get("summary", ""),
        })
    return out

# ── FastAPI ───────────────────────────────────────────────────────────────────
app = FastAPI(title="RAG Chat")
logging.basicConfig(level=logging.WARNING)

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    top_k:   int = 8

SYSTEM_PROMPT = """You are a knowledgeable medical and scientific research assistant for Syneos Health, \
with access to a curated library of scientific papers, clinical studies, and healthcare documents.

When answering:
1. Base your answer primarily on the provided document context
2. Cite sources inline using [Author Year] or [Source N] format when referencing specific data
3. Be precise with statistics, figures, and findings from the papers
4. If the context is insufficient, acknowledge the gap but still provide what you know
5. Structure longer answers with clear headings and bullet points where appropriate

Retrieved context from the document library:
{context}"""

# ── Chat endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    sources = retrieve_context(req.message, req.top_k)
    context_parts = []
    for i, s in enumerate(sources):
        label = s["title"] or s["source_file"] or f"Document {i+1}"
        context_parts.append(f"[Source {i+1}: {label}]\n{s['text'][:1200]}")
    context_text = "\n\n---\n\n".join(context_parts)
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(context=context_text)}]
    for h in req.history[-12:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    async def generate():
        yield "data: " + json.dumps({"type": "sources", "sources": sources}) + "\n\n"
        try:
            client = OpenAI(api_key=OPENAI_API_KEY)
            stream  = client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, stream=True,
                temperature=0.2, max_tokens=1500,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield "data: " + json.dumps({"type": "chunk", "text": delta}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"type": "error", "message": str(e)}) + "\n\n"
        yield "data: " + json.dumps({"type": "done"}) + "\n\n"

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── Chat with file analysis ───────────────────────────────────────────────────
ALLOWED_EXTS = {".pdf", ".docx", ".doc", ".txt", ".json", ".xlsx", ".xls"}

def _sse(t: str, **kw) -> str:
    return "data: " + json.dumps({"type": t, **kw}) + "\n\n"

@app.post("/chat/analyze")
async def chat_analyze(
    file:    UploadFile = File(...),
    message: str        = Form(""),
    history: str        = Form("[]"),
    top_k:   int        = Form(12),
):
    import etl_local as etl

    orig_name = file.filename or "document"
    suffix    = Path(orig_name).suffix.lower()
    contents  = await file.read()

    def generate():
        if suffix not in ALLOWED_EXTS:
            yield _sse("error", message=f"Unsupported file type: {suffix}")
            return

        tmp_dir  = Path(tempfile.mkdtemp())
        tmp_path = tmp_dir / orig_name
        try:
            tmp_path.write_bytes(contents)

            # Extract text
            document = etl.extract_file(tmp_path)
            if not document or not document.get("text_data"):
                yield _sse("error", message="Could not extract text from file.")
                return

            full_text = document.get("full_text", "") or "\n".join(
                d["text"] for d in document["text_data"]
            )

            # Find DOIs in the uploaded document
            doi_pattern = r'\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b'
            dois_found  = list(set(re.findall(doi_pattern, full_text)))[:8]

            # Query ChromaDB with document text
            query_text = full_text[:4000]
            sources    = retrieve_context(query_text, top_k=top_k)
            seen_ids   = {s["id"] for s in sources}

            # Additional targeted searches for each DOI found
            for doi in dois_found:
                for s in retrieve_context(doi, top_k=3):
                    if s["id"] not in seen_ids:
                        sources.append(s)
                        seen_ids.add(s["id"])

            # Also search using the user's message if provided
            if message.strip():
                for s in retrieve_context(message, top_k=6):
                    if s["id"] not in seen_ids:
                        sources.append(s)
                        seen_ids.add(s["id"])

            yield _sse("sources", sources=sources)

            # Build system prompt
            doc_preview = full_text[:8000]
            context_parts = []
            for i, s in enumerate(sources[:15]):
                label = s["title"] or s["source_file"] or f"Source {i+1}"
                context_parts.append(f"[Database Source {i+1}: {label}]\n{s['text'][:900]}")
            context_text = "\n\n---\n\n".join(context_parts)

            doi_note = ""
            if dois_found:
                doi_note = f"\n\nDOIs detected in the uploaded document: {', '.join(dois_found)}"

            system = f"""You are a scientific reference analysis assistant for Syneos Health.

The user has uploaded a document for analysis. Your tasks:
1. Identify all references and citations mentioned in the uploaded document
2. Match each reference to the database sources provided (by title, author, DOI, or content)
3. For each match, state clearly: "Reference found in database: [title/source]"
4. Note any references in the uploaded document that are NOT found in the database
5. Answer any specific question the user has about the document or its references

UPLOADED DOCUMENT ({orig_name}):
{doc_preview}{doi_note}

DATABASE SOURCES (from the knowledge base):
{context_text}"""

            hist     = json.loads(history)
            user_msg = message.strip() or f"Analyse the references in this document and match them to the database."
            messages_list = [{"role": "system", "content": system}]
            for h in hist[-8:]:
                messages_list.append({"role": h["role"], "content": h["content"]})
            messages_list.append({"role": "user", "content": user_msg})

            client = OpenAI(api_key=OPENAI_API_KEY)
            stream = client.chat.completions.create(
                model="gpt-4o-mini", messages=messages_list, stream=True,
                temperature=0.2, max_tokens=2000,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield _sse("chunk", text=delta)

            yield _sse("done")

        except Exception as e:
            import traceback
            yield _sse("error", message=str(e), detail=traceback.format_exc())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── Upload endpoint ───────────────────────────────────────────────────────────
@app.post("/upload/stream")
async def upload_stream(file: UploadFile = File(...)):
    import etl_local as etl

    orig_name = file.filename or "upload"
    suffix    = Path(orig_name).suffix.lower()
    contents  = await file.read()

    def generate():
        if suffix not in ALLOWED_EXTS:
            yield _sse("error", message=f"Unsupported file type: {suffix}")
            return

        tmp_dir  = Path(tempfile.mkdtemp())
        tmp_path = tmp_dir / orig_name
        try:
            tmp_path.write_bytes(contents)
            yield _sse("progress", step="extract", message=f"Extracting text from {orig_name}...", pct=5)

            document = etl.extract_file(tmp_path)
            if not document or not document.get("text_data"):
                yield _sse("error", message="Could not extract text from file.")
                return

            n_blocks = sum(1 for d in document["text_data"] if d.get("text", "").strip())
            yield _sse("progress", step="metadata", message=f"Extracted {n_blocks} text blocks. Fetching metadata...", pct=15)

            doi, meta_crossref = None, {}
            if suffix == ".pdf":
                doi = etl.extract_doi_from_pdf(tmp_path)
                if doi:
                    yield _sse("progress", step="crossref", message=f"DOI found: {doi}. Querying Crossref...", pct=20)
                    meta_crossref = etl.fetch_crossref_metadata(doi)

            full_text = document.get("full_text", "") or "\n".join(
                d["text"] for d in document["text_data"]
            )

            client = etl.get_openai_client()
            if client is None:
                yield _sse("error", message="OpenAI API unavailable.")
                return

            yield _sse("progress", step="title", message="Generating title...", pct=25)
            ai_title    = etl.extract_title_from_text(client, full_text)
            final_title = meta_crossref.get("title") or ai_title or document.get("title", orig_name)

            yield _sse("progress", step="summary", message="Generating summary...", pct=35)
            summary = etl.generate_summary(client, full_text)

            col          = get_collection()
            existing_ids = set(col.get(include=[])["ids"])
            all_chunks   = []
            for page_data in document["text_data"]:
                text = page_data.get("text", "").strip()
                if not text:
                    continue
                for i, chunk in enumerate(etl.chunk_text(text)):
                    if chunk.strip():
                        cid = f"{orig_name}--p{page_data.get('page_number', 1)}--c{i}"
                        all_chunks.append((cid, chunk, page_data))

            yield _sse("progress", step="embed",
                       message=f"Embedding {len(all_chunks)} chunks into ChromaDB...", pct=40)

            meta_base = {
                "source_file":    orig_name,
                "title":          (final_title or "")[:500],
                "authors":        (meta_crossref.get("authors") or "")[:500],
                "published":      (meta_crossref.get("published") or ""),
                "doi":            (meta_crossref.get("doi") or doi or ""),
                "citation":       (meta_crossref.get("Citation") or "")[:1000],
                "citation_count": meta_crossref.get("citation_count", 0),
                "summary":        (summary or "")[:1000],
                "file_type":      suffix.replace(".", ""),
            }

            added = skipped = 0
            BATCH = 50
            total = len(all_chunks)

            for batch_start in range(0, total, BATCH):
                batch = all_chunks[batch_start : batch_start + BATCH]
                ids, docs, metas = [], [], []
                for idx, (cid, chunk, page_data) in enumerate(batch):
                    if cid in existing_ids:
                        skipped += 1
                        continue
                    ids.append(cid)
                    docs.append(chunk)
                    metas.append({
                        **meta_base,
                        "chunk_index":    batch_start + idx,
                        "page_reference": f"p. {page_data.get('page_number', 1)}",
                        "is_table":       str(page_data.get("is_table", False)),
                    })
                    existing_ids.add(cid)
                    added += 1
                if ids:
                    col.add(ids=ids, documents=docs, metadatas=metas)
                pct = 40 + round((batch_start + BATCH) / max(total, 1) * 58)
                yield _sse("progress", step="embed",
                           message=f"Embedding... {min(pct, 98)}%", pct=min(pct, 98))

            yield _sse("done",
                       message=f"Done! Added {added} chunks ({skipped} already existed).",
                       title=final_title,
                       summary=(summary or "")[:300],
                       chunks_added=added,
                       chunks_skipped=skipped,
                       total_chunks=col.count())

        except Exception as e:
            import traceback
            yield _sse("error", message=str(e), detail=traceback.format_exc())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return StreamingResponse(
        generate(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ── Library endpoints ─────────────────────────────────────────────────────────
@app.get("/documents")
async def list_documents():
    col    = get_collection()
    result = col.get(include=["metadatas"])
    docs: dict = {}
    for meta in result["metadatas"]:
        sf = meta.get("source_file", "")
        if not sf:
            continue
        if sf not in docs:
            docs[sf] = {
                "source_file":  sf,
                "title":        meta.get("title", ""),
                "authors":      meta.get("authors", ""),
                "published":    meta.get("published", ""),
                "doi":          meta.get("doi", ""),
                "summary":      meta.get("summary", ""),
                "file_type":    meta.get("file_type", ""),
                "chunk_count":  0,
            }
        docs[sf]["chunk_count"] += 1
    return {"documents": sorted(docs.values(), key=lambda x: x["source_file"].lower())}

@app.delete("/documents/{source_file:path}")
async def delete_document(source_file: str):
    col    = get_collection()
    result = col.get(where={"source_file": source_file}, include=[])
    ids    = result["ids"]
    if not ids:
        raise HTTPException(status_code=404, detail="Document not found in index.")
    col.delete(ids=ids)
    return {"deleted": len(ids), "source_file": source_file, "total_chunks": col.count()}

# ── Status ────────────────────────────────────────────────────────────────────
@app.get("/status")
async def status():
    try:
        col = get_collection()
        return {"status": "ok", "chunks": col.count(), "collection": COLLECTION_NAME}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# ── UI ────────────────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Syneos RAG Assistant</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
:root {
  --bg:#212121; --sidebar:#171717; --surface:#2f2f2f; --surface2:#383838;
  --border:#333; --text:#ececec; --muted:#999; --faint:#555;
  --orange:#E87722; --red:#CC2229; --green:#4caf50; --blue:#5a8cff;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,'Segoe UI',sans-serif;background:var(--bg);
     color:var(--text);height:100vh;display:flex;overflow:hidden;font-size:15px}

/* Sidebar */
.sidebar{width:240px;background:var(--sidebar);display:flex;flex-direction:column;
         border-right:1px solid var(--border);flex-shrink:0}
.sidebar-top{padding:14px 12px;border-bottom:1px solid var(--border)}
.brand{display:flex;align-items:center;gap:10px;margin-bottom:14px}
.brand-icon{width:32px;height:32px;background:linear-gradient(135deg,var(--orange),var(--red));
            border-radius:8px;display:flex;align-items:center;justify-content:center;
            font-weight:800;font-size:13px;color:#fff;flex-shrink:0}
.brand-name{font-weight:700;font-size:.88rem;line-height:1.3}
.brand-name span{display:block;font-size:.7rem;font-weight:400;color:var(--muted)}

.nav{display:flex;flex-direction:column;gap:2px;margin-bottom:10px}
.nav-btn{width:100%;padding:9px 12px;background:transparent;border:none;
         border-radius:7px;color:var(--muted);font-size:.84rem;cursor:pointer;
         display:flex;align-items:center;gap:9px;transition:all .15s;text-align:left}
.nav-btn:hover{background:var(--surface);color:var(--text)}
.nav-btn.active{background:var(--surface);color:var(--text);font-weight:600}
.nav-btn svg{flex-shrink:0;opacity:.7}
.nav-btn.active svg{opacity:1}
.new-btn{width:100%;padding:8px 12px;background:transparent;border:1px solid var(--border);
         border-radius:7px;color:var(--muted);font-size:.82rem;cursor:pointer;
         display:flex;align-items:center;gap:8px;transition:background .15s}
.new-btn:hover{background:var(--surface)}

.sidebar-list{flex:1;overflow-y:auto;padding:8px 8px 0}
.s-label{font-size:.66rem;text-transform:uppercase;letter-spacing:.07em;
         color:var(--faint);padding:6px 8px 3px;font-weight:600}
.hist-item{padding:7px 9px;border-radius:7px;font-size:.8rem;color:var(--muted);
           cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
           transition:background .12s}
.hist-item:hover{background:var(--surface);color:var(--text)}
.sidebar-foot{padding:12px 14px;border-top:1px solid var(--border);font-size:.7rem;color:var(--faint)}
#db-status{margin-top:4px}
.dot{display:inline-block;width:7px;height:7px;border-radius:50%;
     background:var(--faint);margin-right:5px;vertical-align:middle}
.dot.ok{background:var(--green)}

/* Main */
.main{flex:1;display:flex;flex-direction:column;min-width:0;overflow:hidden}
.view{display:none;flex:1;flex-direction:column;overflow:hidden}
.view.active{display:flex}

/* ── CHAT ── */
#chat{flex:1;overflow-y:auto;scroll-behavior:smooth}
#chat::-webkit-scrollbar{width:5px}
#chat::-webkit-scrollbar-thumb{background:var(--surface2);border-radius:3px}

.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;
         height:100%;padding:40px 24px;text-align:center}
.welcome h1{font-size:1.5rem;font-weight:700;margin-bottom:10px}
.welcome p{color:var(--muted);max-width:480px;line-height:1.7;font-size:.88rem}
.chips{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:20px;max-width:600px}
.chip{padding:8px 14px;background:var(--surface);border:1px solid var(--border);
      border-radius:20px;font-size:.8rem;color:var(--muted);cursor:pointer;transition:all .15s}
.chip:hover{border-color:var(--orange);color:var(--text)}

.row{padding:18px 0;border-bottom:1px solid #2a2a2a}
.row:last-child{border-bottom:none}
.inner{max-width:780px;margin:0 auto;padding:0 20px;display:flex;gap:13px}
.avatar{width:29px;height:29px;border-radius:6px;flex-shrink:0;
        display:flex;align-items:center;justify-content:center;font-size:.73rem;font-weight:700}
.row.user .avatar{background:#5a4fcf}
.row.user{background:var(--surface)}
.row.bot .avatar{background:linear-gradient(135deg,var(--orange),var(--red))}
.content{flex:1;min-width:0;line-height:1.75}
.content h1,.content h2,.content h3{margin:14px 0 6px;font-weight:600}
.content h1{font-size:1.18rem}.content h2{font-size:1.03rem}
.content h3{font-size:.93rem;color:var(--orange)}
.content p{margin-bottom:10px}
.content ul,.content ol{padding-left:22px;margin-bottom:10px}
.content li{margin-bottom:4px}
.content strong{color:#fff}
.content code{background:var(--surface2);padding:2px 6px;border-radius:4px;
              font-family:monospace;font-size:.87em;color:#f0c060}
.content pre{background:#1a1a1a;border:1px solid var(--border);border-radius:8px;
             padding:14px;overflow-x:auto;margin-bottom:10px}
.content pre code{background:none;padding:0;color:#ddd}
.content blockquote{border-left:3px solid var(--orange);padding-left:14px;color:var(--muted);margin-bottom:10px}
.content table{border-collapse:collapse;width:100%;margin-bottom:10px;font-size:.87rem}
.content th{background:var(--surface2);padding:8px 12px;text-align:left;border:1px solid var(--border)}
.content td{padding:7px 12px;border:1px solid var(--border)}
.content tr:nth-child(even){background:rgba(255,255,255,.03)}

.sources-toggle{margin-top:12px;display:flex;align-items:center;gap:7px;cursor:pointer;
                font-size:.78rem;color:var(--muted);user-select:none;width:fit-content}
.sources-toggle:hover{color:var(--text)}
.toggle-icon{transition:transform .2s;font-size:.68rem;display:inline-block}
.sources-panel{margin-top:8px;display:none}
.sources-panel.open{display:block}
.src-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:7px}
.src-card{background:var(--surface);border:1px solid var(--border);border-radius:8px;
          padding:10px 12px;font-size:.78rem;transition:border-color .15s}
.src-card:hover{border-color:var(--orange)}
.src-title{font-weight:600;color:var(--text);margin-bottom:3px;
           white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src-meta{color:var(--muted);font-size:.71rem;margin-bottom:4px}
.src-score{display:inline-block;background:var(--surface2);border-radius:10px;
           padding:1px 7px;font-size:.68rem;color:var(--orange)}
.src-snippet{color:var(--faint);font-size:.72rem;line-height:1.5;margin-top:5px;
             display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

.msg-actions{display:flex;gap:6px;margin-top:8px}
.act-btn{background:none;border:1px solid var(--border);border-radius:6px;
         color:var(--muted);font-size:.73rem;padding:3px 9px;cursor:pointer;transition:all .12s}
.act-btn:hover{background:var(--surface2);color:var(--text)}

.typing{display:flex;gap:5px;align-items:center;padding:4px 0}
.typing span{width:7px;height:7px;background:var(--muted);border-radius:50%;animation:pulse 1.4s infinite}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes pulse{0%,80%,100%{transform:scale(.6);opacity:.4}40%{transform:scale(1);opacity:1}}
.cursor::after{content:"▋";animation:blink .7s infinite;color:var(--orange)}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}

/* Input area */
.input-area{padding:12px 20px 18px}
.input-wrap{max-width:780px;margin:0 auto;position:relative}

/* Attachment preview */
.attach-preview{display:none;align-items:center;gap:10px;margin-bottom:8px;
                padding:9px 14px;background:var(--surface);border:1px solid var(--orange);
                border-radius:9px;font-size:.82rem}
.attach-preview svg{flex-shrink:0;color:var(--orange)}
.attach-fname{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text)}
.attach-hint{font-size:.72rem;color:var(--muted);white-space:nowrap}
.attach-remove{background:none;border:none;color:var(--muted);cursor:pointer;
               font-size:1.1rem;line-height:1;padding:2px 4px;transition:color .15s}
.attach-remove:hover{color:#f87171}

/* File badge shown in chat bubble */
.file-badge{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;
            background:rgba(232,119,34,.12);border:1px solid rgba(232,119,34,.3);
            border-radius:7px;font-size:.78rem;color:var(--orange);margin-bottom:10px}

textarea#q{width:100%;padding:12px 50px 12px 50px;background:var(--surface);
           border:1px solid #444;border-radius:14px;color:var(--text);
           font-size:.93rem;font-family:inherit;outline:none;resize:none;
           line-height:1.55;min-height:48px;max-height:180px;transition:border-color .15s}
textarea#q:focus{border-color:var(--orange)}
textarea#q::placeholder{color:var(--faint)}
#attach-btn{position:absolute;left:9px;bottom:7px;width:33px;height:33px;
            background:none;border:1px solid var(--border);border-radius:8px;
            color:var(--muted);cursor:pointer;display:flex;align-items:center;
            justify-content:center;transition:all .15s}
#attach-btn:hover{background:var(--surface2);color:var(--text)}
#attach-btn.has-file{border-color:var(--orange);color:var(--orange)}
#send-btn{position:absolute;right:9px;bottom:7px;width:33px;height:33px;
          background:var(--orange);border:none;border-radius:8px;cursor:pointer;
          display:flex;align-items:center;justify-content:center;transition:background .15s}
#send-btn:hover{background:var(--red)}
#send-btn:disabled{background:var(--faint);cursor:not-allowed}
#send-btn svg{width:16px;height:16px;fill:#fff}
.hint{text-align:center;font-size:.7rem;color:var(--faint);margin-top:6px}

/* ── UPLOAD ── */
.upload-view{flex:1;overflow-y:auto;padding:32px 40px}
.upload-view h2{font-size:1.2rem;font-weight:700;margin-bottom:6px}
.upload-view .sub{color:var(--muted);font-size:.86rem;margin-bottom:24px}
.drop-zone{border:2px dashed var(--border);border-radius:14px;padding:48px 24px;
           text-align:center;cursor:pointer;transition:all .2s;margin-bottom:24px}
.drop-zone:hover,.drop-zone.drag-over{border-color:var(--orange);background:rgba(232,119,34,.05)}
.drop-zone svg{margin-bottom:14px;color:var(--muted)}
.drop-zone p{color:var(--muted);font-size:.9rem;margin-bottom:8px}
.drop-zone .exts{font-size:.75rem;color:var(--faint)}
.browse-btn{display:inline-block;margin-top:12px;padding:8px 20px;background:var(--orange);
            color:#fff;border-radius:8px;font-size:.83rem;cursor:pointer;border:none;
            font-family:inherit;transition:background .15s}
.browse-btn:hover{background:var(--red)}
#file-input{display:none}
.upload-list{display:flex;flex-direction:column;gap:10px}
.upload-item{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px}
.upload-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.upload-name{font-size:.85rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:70%}
.upload-status{font-size:.75rem;padding:2px 10px;border-radius:10px;background:var(--surface2);color:var(--muted)}
.upload-status.done{background:rgba(76,175,80,.15);color:var(--green)}
.upload-status.error{background:rgba(204,34,41,.15);color:#f87171}
.progress-bar{height:4px;background:var(--surface2);border-radius:2px;overflow:hidden;margin-bottom:8px}
.progress-fill{height:100%;background:var(--orange);border-radius:2px;transition:width .3s;width:0}
.upload-msg{font-size:.78rem;color:var(--muted);line-height:1.5}
.upload-result{margin-top:8px;padding:10px 12px;background:rgba(76,175,80,.08);
               border:1px solid rgba(76,175,80,.2);border-radius:8px;font-size:.8rem;line-height:1.6}
.upload-result .r-title{font-weight:600;color:var(--text);margin-bottom:4px}
.upload-result .r-summary{color:var(--muted)}

/* ── LIBRARY ── */
.library-view{flex:1;display:flex;flex-direction:column;overflow:hidden;padding:28px 32px 0}
.library-view h2{font-size:1.2rem;font-weight:700;margin-bottom:4px}
.library-view .sub{color:var(--muted);font-size:.84rem;margin-bottom:18px}
.lib-toolbar{display:flex;align-items:center;gap:12px;margin-bottom:16px}
.lib-search{flex:1;padding:9px 14px;background:var(--surface);border:1px solid var(--border);
            border-radius:9px;color:var(--text);font-size:.86rem;outline:none;transition:border-color .15s}
.lib-search:focus{border-color:var(--orange)}
.lib-search::placeholder{color:var(--faint)}
.lib-count{font-size:.78rem;color:var(--muted);white-space:nowrap}
.lib-refresh{padding:8px 14px;background:var(--surface);border:1px solid var(--border);
             border-radius:8px;color:var(--muted);font-size:.8rem;cursor:pointer;transition:all .15s}
.lib-refresh:hover{background:var(--surface2);color:var(--text)}
.lib-table-wrap{flex:1;overflow-y:auto;border:1px solid var(--border);border-radius:10px;margin-bottom:16px}
.lib-table-wrap::-webkit-scrollbar{width:5px}
.lib-table-wrap::-webkit-scrollbar-thumb{background:var(--surface2);border-radius:3px}
table.lib{width:100%;border-collapse:collapse;font-size:.82rem}
table.lib thead th{background:var(--surface);padding:10px 14px;text-align:left;font-weight:600;
                   color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.04em;
                   border-bottom:1px solid var(--border);position:sticky;top:0;z-index:1}
table.lib tbody tr{border-bottom:1px solid #2a2a2a;transition:background .1s}
table.lib tbody tr:last-child{border-bottom:none}
table.lib tbody tr:hover{background:var(--surface)}
table.lib td{padding:10px 14px;vertical-align:top}
.td-file{max-width:220px}
.td-file .fname{font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.td-file .ftype{font-size:.7rem;color:var(--faint);margin-top:2px;text-transform:uppercase}
.td-title{max-width:280px;color:var(--muted);overflow:hidden;
          display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.td-authors{max-width:160px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:.78rem}
.td-pub{color:var(--muted);font-size:.78rem;white-space:nowrap}
.td-chunks{text-align:right;color:var(--orange);font-weight:600;white-space:nowrap}
.td-actions{white-space:nowrap;text-align:right}
.del-btn{background:none;border:1px solid var(--border);border-radius:6px;color:var(--muted);
         font-size:.72rem;padding:3px 10px;cursor:pointer;transition:all .15s}
.del-btn:hover{background:rgba(204,34,41,.15);border-color:#f87171;color:#f87171}
.lib-empty{padding:60px;text-align:center;color:var(--faint);font-size:.9rem}
.lib-loading{padding:60px;text-align:center;color:var(--muted)}
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-top">
    <div class="brand">
      <div class="brand-icon">S</div>
      <div class="brand-name">Syneos Health<span>RAG Assistant</span></div>
    </div>
    <nav class="nav">
      <button class="nav-btn active" id="nav-chat" onclick="switchView('chat')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>Chat
      </button>
      <button class="nav-btn" id="nav-upload" onclick="switchView('upload')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/></svg>Upload Documents
      </button>
      <button class="nav-btn" id="nav-library" onclick="switchView('library')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>Document Library
      </button>
    </nav>
    <button class="new-btn" onclick="newChat()">
      <svg width="13" height="13" viewBox="0 0 14 14" stroke="currentColor" stroke-width="1.8" fill="none">
        <line x1="7" y1="1" x2="7" y2="13"/><line x1="1" y1="7" x2="13" y2="7"/>
      </svg>New chat
    </button>
  </div>
  <div class="sidebar-list">
    <div class="s-label">Recent</div>
    <div id="history"></div>
  </div>
  <div class="sidebar-foot">
    ChromaDB &middot; gpt-4o-mini &middot; text-embedding-3-small
    <div id="db-status"><span class="dot" id="status-dot"></span><span id="status-txt">checking&hellip;</span></div>
  </div>
</div>

<div class="main">

  <!-- CHAT VIEW -->
  <div class="view active" id="view-chat" style="overflow:hidden">
    <div id="chat">
      <div class="welcome" id="welcome">
        <div style="width:52px;height:52px;background:linear-gradient(135deg,#E87722,#CC2229);
                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                    font-size:22px;margin-bottom:16px">&#x1F52C;</div>
        <h1>What would you like to know?</h1>
        <p>Ask a question or attach a document to find its references in the library.</p>
        <div class="chips">
          <div class="chip" onclick="ask(this.textContent)">What is the global incidence of ischaemic stroke?</div>
          <div class="chip" onclick="ask(this.textContent)">Summarise risk factors for recurrent stroke</div>
          <div class="chip" onclick="ask(this.textContent)">What anticoagulants are used after TIA?</div>
          <div class="chip" onclick="ask(this.textContent)">Economic costs of stroke in Europe</div>
          <div class="chip" onclick="ask(this.textContent)">Stroke outcomes and mortality in Africa</div>
          <div class="chip" onclick="ask(this.textContent)">What is the role of factor XIa inhibitors?</div>
        </div>
      </div>
    </div>
    <div class="input-area">
      <div class="input-wrap">
        <!-- Attachment preview -->
        <div class="attach-preview" id="attach-preview">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
          <span class="attach-fname" id="attach-fname"></span>
          <span class="attach-hint">Will be analysed for references</span>
          <button class="attach-remove" onclick="removeAttach()" title="Remove file">&#x2715;</button>
        </div>
        <!-- Input row -->
        <div style="position:relative">
          <button id="attach-btn" title="Attach a document to check for references" onclick="document.getElementById('chat-file-input').click()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
          </button>
          <textarea id="q" rows="1" placeholder="Ask a question, or attach a document to find its references&#8230;"></textarea>
          <button id="send-btn" onclick="sendMsg()">
            <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
          </button>
        </div>
        <input type="file" id="chat-file-input"
               accept=".pdf,.docx,.doc,.txt,.json,.xlsx,.xls"
               onchange="onChatFileSelected(this)">
      </div>
      <div class="hint">Enter to send &middot; Shift+Enter for new line &middot; Paperclip to attach a document for reference analysis</div>
    </div>
  </div>

  <!-- UPLOAD VIEW -->
  <div class="view" id="view-upload">
    <div class="upload-view">
      <h2>Upload Documents</h2>
      <p class="sub">Add PDFs, Word documents, text files, Excel spreadsheets, or JSON files to the knowledge base.</p>
      <div class="drop-zone" id="drop-zone" onclick="document.getElementById('file-input').click()"
           ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event)">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/>
          <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"/>
        </svg>
        <p>Drag &amp; drop files here, or click to browse</p>
        <div class="exts">PDF &bull; DOCX &bull; TXT &bull; XLSX &bull; JSON</div>
        <button class="browse-btn" onclick="event.stopPropagation();document.getElementById('file-input').click()">Browse files</button>
      </div>
      <input type="file" id="file-input" multiple
             accept=".pdf,.docx,.doc,.txt,.json,.xlsx,.xls"
             onchange="onFilesSelected(this.files)">
      <div class="upload-list" id="upload-list"></div>
    </div>
  </div>

  <!-- LIBRARY VIEW -->
  <div class="view" id="view-library" style="overflow:hidden">
    <div class="library-view">
      <h2>Document Library</h2>
      <p class="sub">All documents currently indexed in the knowledge base.</p>
      <div class="lib-toolbar">
        <input class="lib-search" id="lib-search" placeholder="Search by title, filename, or author&hellip;"
               oninput="filterLib(this.value)">
        <span class="lib-count" id="lib-count"></span>
        <button class="lib-refresh" onclick="loadLibrary()">Refresh</button>
      </div>
      <div class="lib-table-wrap">
        <table class="lib">
          <thead>
            <tr>
              <th>File</th><th>Title</th><th>Authors</th>
              <th>Published</th><th style="text-align:right">Chunks</th><th></th>
            </tr>
          </thead>
          <tbody id="lib-body">
            <tr><td colspan="6" class="lib-loading">Loading library&hellip;</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div>

<script>
marked.setOptions({breaks:true, gfm:true});

const chat    = document.getElementById('chat');
const input   = document.getElementById('q');
const btn     = document.getElementById('send-btn');
const welcome = document.getElementById('welcome');
const histEl  = document.getElementById('history');

let history    = [];
let histTitles = [];
let libDocs    = [];
let attachedFile = null;

// ── Status ────────────────────────────────────────────────────────────────────
async function checkStatus() {
  try {
    const r = await fetch('/status');
    const d = await r.json();
    const dot = document.getElementById('status-dot');
    const txt = document.getElementById('status-txt');
    if (d.status === 'ok') {
      dot.className = 'dot ok';
      txt.textContent = d.chunks.toLocaleString() + ' chunks indexed';
    } else { txt.textContent = 'DB error'; }
  } catch { document.getElementById('status-txt').textContent = 'offline'; }
}
checkStatus();

// ── View switching ─────────────────────────────────────────────────────────────
function switchView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  document.getElementById('nav-' + name).classList.add('active');
  if (name === 'library') loadLibrary();
}

// ── Chat input ─────────────────────────────────────────────────────────────────
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 180) + 'px';
});
input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMsg(); }
});
input.focus();

function newChat() {
  history = [];
  chat.innerHTML = '';
  chat.appendChild(welcome);
  welcome.style.display = 'flex';
  switchView('chat');
  removeAttach();
}

function ask(text) { switchView('chat'); input.value = text; sendMsg(); }

function addHistory(q) {
  const label = q.length > 52 ? q.slice(0, 49) + '...' : q;
  histTitles.unshift(label);
  if (histTitles.length > 14) histTitles.pop();
  histEl.innerHTML = histTitles.map(t =>
    `<div class="hist-item" onclick="ask(${JSON.stringify(t)})">&#x1F4AC; ${esc(t)}</div>`
  ).join('');
}

// ── File attachment in chat ───────────────────────────────────────────────────
function onChatFileSelected(input) {
  if (input.files[0]) {
    attachedFile = input.files[0];
    document.getElementById('attach-fname').textContent = attachedFile.name;
    document.getElementById('attach-preview').style.display = 'flex';
    document.getElementById('attach-btn').classList.add('has-file');
  }
  input.value = '';
}

function removeAttach() {
  attachedFile = null;
  document.getElementById('attach-preview').style.display = 'none';
  document.getElementById('attach-btn').classList.remove('has-file');
}

// ── Send message ──────────────────────────────────────────────────────────────
async function sendMsg() {
  const text = input.value.trim();
  if (!text && !attachedFile) return;
  if (btn.disabled) return;

  input.value = ''; input.style.height = 'auto';
  welcome.style.display = 'none';
  btn.disabled = true;

  const file = attachedFile;
  removeAttach();

  const displayMsg = text || (file ? `Analyse references in: ${file.name}` : '');
  addHistory(displayMsg);

  // User bubble (shows file badge if file attached)
  const userHtml = (file
    ? `<div class="file-badge"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>${esc(file.name)}</div>`
    : '') + (text ? `<p>${esc(text)}</p>` : '');
  appendRow('user', userHtml);

  // Bot typing bubble
  const botRow = document.createElement('div');
  botRow.className = 'row bot';
  botRow.innerHTML = '<div class="inner"><div class="avatar">S</div>' +
    '<div class="content"><div class="typing"><span></span><span></span><span></span></div></div></div>';
  chat.appendChild(botRow);
  scrollBottom();

  const contentEl = botRow.querySelector('.content');
  let fullText = '', sources = [], textDiv = null;

  try {
    let resp;
    if (file) {
      // File analysis endpoint
      const fd = new FormData();
      fd.append('file', file);
      fd.append('message', text);
      fd.append('history', JSON.stringify(history.slice(-8)));
      fd.append('top_k', '12');
      resp = await fetch('/chat/analyze', {method: 'POST', body: fd});
    } else {
      // Regular chat endpoint
      resp = await fetch('/chat/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: text, history: history.slice(-12), top_k: 8})
      });
    }

    const reader = resp.body.getReader();
    const dec    = new TextDecoder();
    let buf = '';

    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      buf += dec.decode(value, {stream: true});
      const parts = buf.split('\n\n');
      buf = parts.pop();

      for (const part of parts) {
        if (!part.startsWith('data: ')) continue;
        let ev;
        try { ev = JSON.parse(part.slice(6)); } catch { continue; }

        if (ev.type === 'sources') {
          sources = ev.sources;
          contentEl.innerHTML = '';
          textDiv = document.createElement('div');
          textDiv.className = 'cursor';
          contentEl.appendChild(textDiv);
        } else if (ev.type === 'chunk') {
          fullText += ev.text;
          if (textDiv) textDiv.innerHTML = marked.parse(fullText);
          scrollBottom();
        } else if (ev.type === 'done') {
          if (textDiv) textDiv.classList.remove('cursor');
          buildSourcesPanel(contentEl, sources, file ? 'References found in database' : null);
          buildActions(contentEl, fullText);
          history.push({role:'user', content: displayMsg});
          history.push({role:'assistant', content: fullText});
        } else if (ev.type === 'error') {
          contentEl.innerHTML = '<p style="color:#f87171">&#x26A0; ' + esc(ev.message) + '</p>';
        }
      }
    }
  } catch (err) {
    contentEl.innerHTML = '<p style="color:#f87171">Network error: ' + esc(err.message) + '</p>';
  }

  btn.disabled = false;
  scrollBottom();
  input.focus();
}

function appendRow(role, html) {
  const row = document.createElement('div');
  row.className = 'row ' + role;
  row.innerHTML = '<div class="inner"><div class="avatar">' +
    (role === 'user' ? 'U' : 'S') + '</div><div class="content">' + html + '</div></div>';
  chat.appendChild(row);
  scrollBottom();
}

function buildSourcesPanel(parent, sources, label) {
  if (!sources || !sources.length) return;
  const wrap  = document.createElement('div');
  const cards = sources.map(s => {
    const title     = esc(s.title || s.source_file || 'Unknown source');
    const authShort = s.authors ? esc(s.authors.split(',')[0] + (s.authors.includes(',') ? ' et al.' : '')) : '';
    const year      = s.published ? esc(s.published.slice(0,4)) : '';
    const meta      = [authShort, year].filter(Boolean).join(' · ');
    const score     = (s.similarity * 100).toFixed(1);
    const snippet   = esc((s.text || '').slice(0, 120));
    const page      = s.page_reference ? `<div class="src-meta" style="margin-top:3px">${esc(s.page_reference)}</div>` : '';
    return `<div class="src-card">
      <div class="src-title" title="${title}">${title}</div>
      ${meta ? `<div class="src-meta">${meta}</div>` : ''}
      <span class="src-score">${score}% match</span>${page}
      <div class="src-snippet">${snippet}</div>
    </div>`;
  }).join('');
  const toggleLabel = label || `${sources.length} source${sources.length !== 1 ? 's' : ''} retrieved`;
  wrap.innerHTML = `<div class="sources-toggle" onclick="toggleSrc(this)">
    <span class="toggle-icon">&#x25B6;</span>
    <span>${esc(toggleLabel)}</span>
  </div>
  <div class="sources-panel"><div class="src-grid">${cards}</div></div>`;
  parent.appendChild(wrap);
}

function toggleSrc(el) {
  const panel = el.nextElementSibling;
  const icon  = el.querySelector('.toggle-icon');
  panel.classList.toggle('open');
  icon.style.transform = panel.classList.contains('open') ? 'rotate(90deg)' : '';
}

function buildActions(parent, text) {
  const div = document.createElement('div');
  div.className = 'msg-actions';
  const b = document.createElement('button');
  b.className = 'act-btn'; b.textContent = 'Copy';
  b.onclick = () => {
    navigator.clipboard.writeText(text).then(() => {
      b.textContent = 'Copied!';
      setTimeout(() => b.textContent = 'Copy', 1600);
    });
  };
  div.appendChild(b);
  parent.appendChild(div);
}

function scrollBottom() { chat.scrollTop = chat.scrollHeight; }
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
}

// ── Upload (to DB) ────────────────────────────────────────────────────────────
function onDragOver(e)  { e.preventDefault(); document.getElementById('drop-zone').classList.add('drag-over'); }
function onDragLeave(e) { document.getElementById('drop-zone').classList.remove('drag-over'); }
function onDrop(e) {
  e.preventDefault();
  document.getElementById('drop-zone').classList.remove('drag-over');
  onFilesSelected(e.dataTransfer.files);
}
function onFilesSelected(files) {
  for (const file of files) uploadFile(file);
  document.getElementById('file-input').value = '';
}

function uploadFile(file) {
  const list   = document.getElementById('upload-list');
  const itemId = 'up-' + Date.now() + Math.random().toString(36).slice(2);
  const div    = document.createElement('div');
  div.className = 'upload-item'; div.id = itemId;
  div.innerHTML = `
    <div class="upload-header">
      <div class="upload-name" title="${esc(file.name)}">${esc(file.name)}</div>
      <div class="upload-status" id="${itemId}-status">Queued</div>
    </div>
    <div class="progress-bar"><div class="progress-fill" id="${itemId}-bar"></div></div>
    <div class="upload-msg" id="${itemId}-msg">Starting&hellip;</div>`;
  list.prepend(div);

  const statusEl = document.getElementById(itemId + '-status');
  const barEl    = document.getElementById(itemId + '-bar');
  const msgEl    = document.getElementById(itemId + '-msg');
  statusEl.textContent = 'Processing';

  const fd = new FormData(); fd.append('file', file);
  fetch('/upload/stream', {method:'POST', body:fd})
    .then(async resp => {
      const reader = resp.body.getReader();
      const dec    = new TextDecoder();
      let buf = '';
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream:true});
        const parts = buf.split('\n\n'); buf = parts.pop();
        for (const part of parts) {
          if (!part.startsWith('data: ')) continue;
          let ev; try { ev = JSON.parse(part.slice(6)); } catch { continue; }
          if (ev.type === 'progress') {
            msgEl.textContent = ev.message || '';
            if (ev.pct != null) barEl.style.width = ev.pct + '%';
          } else if (ev.type === 'done') {
            barEl.style.width = '100%';
            statusEl.textContent = 'Done'; statusEl.className = 'upload-status done';
            msgEl.innerHTML = `<div class="upload-result">
              <div class="r-title">${esc(ev.title || file.name)}</div>
              <div class="r-summary">${esc(ev.summary || '')}</div>
              <div style="margin-top:6px;color:var(--green);font-size:.75rem">
                +${ev.chunks_added} chunks &bull; ${ev.total_chunks.toLocaleString()} total in DB
              </div></div>`;
            checkStatus();
          } else if (ev.type === 'error') {
            barEl.style.width = '100%'; barEl.style.background = 'var(--red)';
            statusEl.textContent = 'Error'; statusEl.className = 'upload-status error';
            msgEl.innerHTML = `<span style="color:#f87171">${esc(ev.message)}</span>`;
          }
        }
      }
    })
    .catch(err => {
      statusEl.textContent = 'Error'; statusEl.className = 'upload-status error';
      msgEl.innerHTML = `<span style="color:#f87171">${esc(err.message)}</span>`;
    });
}

// ── Library ───────────────────────────────────────────────────────────────────
async function loadLibrary() {
  const tbody = document.getElementById('lib-body');
  tbody.innerHTML = '<tr><td colspan="6" class="lib-loading">Loading&hellip;</td></tr>';
  document.getElementById('lib-count').textContent = '';
  try {
    const r = await fetch('/documents');
    const d = await r.json();
    libDocs = d.documents;
    renderLib(libDocs);
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="6" class="lib-empty" style="color:#f87171">Failed: ${esc(e.message)}</td></tr>`;
  }
}

function renderLib(docs) {
  const tbody = document.getElementById('lib-body');
  document.getElementById('lib-count').textContent = `${docs.length} document${docs.length!==1?'s':''}`;
  if (!docs.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="lib-empty">No documents indexed yet.</td></tr>';
    return;
  }
  tbody.innerHTML = docs.map(d => {
    const ext     = (d.file_type||d.source_file.split('.').pop()||'').toUpperCase();
    const authors = d.authors ? d.authors.split(',')[0].trim() + (d.authors.includes(',') ? ' et al.' : '') : '';
    const pub     = d.published ? d.published.slice(0,4) : '';
    return `<tr>
      <td class="td-file"><div class="fname" title="${esc(d.source_file)}">${esc(d.source_file)}</div><div class="ftype">${esc(ext)}</div></td>
      <td class="td-title">${esc(d.title||'—')}</td>
      <td class="td-authors">${esc(authors||'—')}</td>
      <td class="td-pub">${esc(pub||'—')}</td>
      <td class="td-chunks">${d.chunk_count.toLocaleString()}</td>
      <td class="td-actions"><button class="del-btn" onclick="deleteDoc(${JSON.stringify(d.source_file)},this)">Delete</button></td>
    </tr>`;
  }).join('');
}

function filterLib(q) {
  q = q.toLowerCase();
  if (!q) { renderLib(libDocs); return; }
  renderLib(libDocs.filter(d =>
    (d.source_file||'').toLowerCase().includes(q)||
    (d.title||'').toLowerCase().includes(q)||
    (d.authors||'').toLowerCase().includes(q)
  ));
}

async function deleteDoc(sourceFile, btn) {
  if (!confirm(`Delete all indexed chunks for:\n\n${sourceFile}\n\nThis cannot be undone.`)) return;
  btn.disabled = true; btn.textContent = 'Deleting...';
  try {
    const r = await fetch('/documents/' + encodeURIComponent(sourceFile), {method:'DELETE'});
    if (!r.ok) throw new Error(await r.text());
    libDocs = libDocs.filter(x => x.source_file !== sourceFile);
    const q = document.getElementById('lib-search').value.toLowerCase();
    renderLib(q ? libDocs.filter(d =>
      (d.source_file||'').toLowerCase().includes(q)||
      (d.title||'').toLowerCase().includes(q)||
      (d.authors||'').toLowerCase().includes(q)
    ) : libDocs);
    checkStatus();
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Delete';
    alert('Delete failed: ' + e.message);
  }
}
</script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def ui():
    return HTML
