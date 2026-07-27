from __future__ import annotations

import html
import json
import time
from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from knowledge_hub_service import (
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    DuplicateDocumentError,
    KnowledgeHubError,
    create_scoped_file_url,
    delete_document,
    generate_grounded_answer,
    get_active_session,
    get_document_chunks,
    get_document_images,
    get_document_pages,
    list_active_collections,
    list_accessible_collections,
    list_queued_jobs,
    list_library,
    log_event,
    process_document,
    quality_summary,
    read_staged_file_bytes,
    reconcile_automatic_lifecycle,
    recent_events,
    register_upload,
    recover_queued_jobs,
    reprocess_document,
    search_knowledge,
    scalar,
    unpublish_document,
    viewer_permissions,
)


CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+Pro:wght@400&display=swap');

:root {
    --color-notion-blue: #0075de;
    --color-paper-warmth: #f6f5f4;
    --color-pure-white: #ffffff;
    --color-ink-black: #000000;
    --color-charcoal: #111111;
    --color-stone: #757575;
    --color-graphite: #615d59;
    --color-slate: #696969;
    --color-sky-tint: #e6f3fe;
    --color-marigold: #ffb110;
    --color-coral: #f64932;
    --color-saffron: #e89d01;
    --color-vermillion: #e32d14;
    --color-mocha: #b18164;
    --color-signal-blue: #097fe8;
    --color-sky-wash: #62aef0;
    --color-midnight-ink: #02093a;
    --font-notioninter: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-lyon-text: 'Source Serif Pro', Georgia, serif;
    --text-caption: 12px;
    --text-body-sm: 14px;
    --text-body: 16px;
    --text-heading-sm: 22px;
    --text-display-sm: 54px;
    --spacing-4: 4px;
    --spacing-8: 8px;
    --spacing-12: 12px;
    --spacing-16: 16px;
    --spacing-20: 20px;
    --spacing-24: 24px;
    --spacing-28: 28px;
    --spacing-32: 32px;
    --spacing-36: 36px;
    --spacing-64: 64px;
    --spacing-80: 80px;
    --radius-small: 4px;
    --radius-buttons: 8px;
    --radius-cards: 12px;
    --radius-pills: 9999px;
    --hairline: rgba(0, 0, 0, 0.08);
}

html, body, [class*="css"], .stApp {
    font-family: var(--font-notioninter) !important;
}

.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background: var(--color-paper-warmth) !important;
    color: rgba(0, 0, 0, 0.95) !important;
}

.main .block-container {
    max-width: 1440px;
    padding-top: var(--spacing-32);
    padding-bottom: var(--spacing-80);
}

h1, h2, h3, h4, p, label, .stMarkdown, .stCaption {
    font-family: var(--font-notioninter) !important;
}

h1, h2, h3, h4 {
    color: var(--color-ink-black) !important;
    letter-spacing: -0.011em;
}

p, label, [data-testid="stCaptionContainer"] {
    color: rgba(0, 0, 0, 0.60) !important;
}

.kh-header {
    position: relative;
    overflow: hidden;
    background: var(--color-pure-white);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-cards);
    padding: var(--spacing-20) var(--spacing-28);
    margin-bottom: var(--spacing-20);
}

.kh-mark-row {
    display: flex;
    gap: var(--spacing-8);
    margin-bottom: var(--spacing-12);
}

.kh-mark {
    width: 18px;
    height: 18px;
    border-radius: var(--radius-pills);
    background: var(--color-pure-white);
    border: 2px solid var(--mark-color);
    transition: transform 200ms ease;
}

.kh-mark:nth-child(1) { --mark-color: var(--color-signal-blue); }
.kh-mark:nth-child(2) { --mark-color: var(--color-coral); }
.kh-mark:nth-child(3) { --mark-color: var(--color-marigold); }
.kh-mark:nth-child(4) { --mark-color: var(--color-sky-wash); }
.kh-header:hover .kh-mark:nth-child(odd) { transform: translateY(-2px); }

.kh-kicker {
    color: rgba(0, 0, 0, 0.60);
    font-size: var(--text-caption);
    font-weight: 500;
    letter-spacing: 0.12px;
    text-transform: uppercase;
}

.kh-title {
    color: var(--color-ink-black);
    font-size: var(--text-display-sm);
    font-weight: 600;
    letter-spacing: -1.89px;
    line-height: 1.04;
    margin-top: 0;
    max-width: 900px;
}

.kh-highlight {
    display: inline-block;
    background: var(--color-marigold);
    color: var(--color-ink-black);
    border-radius: var(--radius-pills);
    padding: 2px 18px 5px 18px;
    white-space: nowrap;
}

.kh-subtitle {
    color: var(--color-graphite);
    font-family: var(--font-lyon-text) !important;
    font-size: 18px;
    line-height: 1.56;
    max-width: 760px;
    margin-top: var(--spacing-20);
}

.kh-card,
.kh-answer {
    background: var(--color-pure-white);
    border: 1px solid var(--hairline);
    border-radius: var(--radius-cards);
    padding: var(--spacing-24);
    margin: var(--spacing-12) 0;
    box-shadow: none;
    transition: border-color 200ms ease, background-color 200ms ease;
}

.kh-card:hover {
    border-color: rgba(0, 0, 0, 0.24);
}

.kh-card-title {
    color: var(--color-ink-black);
    font-size: var(--text-heading-sm);
    font-weight: 700;
    letter-spacing: -0.242px;
    line-height: 1.27;
    margin-bottom: var(--spacing-8);
}

.kh-card-meta {
    color: rgba(0, 0, 0, 0.40);
    font-size: var(--text-caption);
    line-height: 1.33;
    letter-spacing: 0.12px;
    margin-bottom: var(--spacing-16);
}

.kh-card-body {
    color: var(--color-graphite);
    font-size: var(--text-body);
    line-height: 1.5;
    white-space: pre-wrap;
}

.kh-callout {
    background: var(--color-sky-tint);
    color: rgba(0, 0, 0, 0.95);
    border-radius: var(--radius-cards);
    padding: var(--spacing-24);
    margin: var(--spacing-16) 0;
    border: 0;
}

.kh-answer {
    border-left: 6px solid var(--color-notion-blue);
}

.kh-status {
    display: inline-block;
    background: var(--color-sky-tint);
    border: 0;
    border-radius: var(--radius-pills);
    color: var(--color-notion-blue);
    font-size: var(--text-caption);
    font-weight: 500;
    padding: var(--spacing-4) var(--spacing-12);
    margin-right: var(--spacing-4);
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stFormSubmitButton"] > button {
    min-height: 34px;
    border-radius: var(--radius-buttons) !important;
    border: 0 !important;
    background: var(--color-sky-tint) !important;
    color: var(--color-notion-blue) !important;
    font-size: var(--text-body-sm) !important;
    font-weight: 500 !important;
    padding: 6px 15px !important;
    box-shadow: none !important;
    transition: background-color 200ms ease, color 200ms ease !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background: var(--color-sky-tint) !important;
    color: var(--color-notion-blue) !important;
    filter: brightness(0.97);
}

.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"] {
    background: var(--color-notion-blue) !important;
    color: var(--color-pure-white) !important;
}

.stButton > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
    background: var(--color-notion-blue) !important;
    opacity: 0.90;
}

.stButton > button:focus-visible,
[data-testid="stFormSubmitButton"] > button:focus-visible,
input:focus-visible,
textarea:focus-visible {
    outline: 3px solid rgba(0, 117, 222, 0.25) !important;
    outline-offset: 2px !important;
}

[data-baseweb="input"] > div,
[data-baseweb="textarea"] > div,
[data-baseweb="select"] > div,
[data-testid="stFileUploaderDropzone"],
[data-testid="stDateInput"] > div > div {
    background: var(--color-pure-white) !important;
    border-color: var(--hairline) !important;
    border-radius: var(--radius-buttons) !important;
    box-shadow: none !important;
}

input, textarea, [data-baseweb="select"] * {
    color: rgba(0, 0, 0, 0.95) !important;
}

[data-testid="stForm"],
[data-testid="stExpander"],
[data-testid="stDataFrame"],
[data-testid="stMetric"] {
    background: var(--color-pure-white) !important;
    border: 1px solid var(--hairline) !important;
    border-radius: var(--radius-cards) !important;
    box-shadow: none !important;
}

[data-testid="stForm"] {
    padding: var(--spacing-24) !important;
}

[data-testid="stMetric"] {
    padding: var(--spacing-20) !important;
}

[data-baseweb="tab-list"] {
    gap: var(--spacing-8);
    border-bottom: 1px solid var(--hairline);
    background: transparent !important;
}

[data-testid="stTabs"] button[data-baseweb="tab"],
[data-testid="stTabs"] button[role="tab"],
[data-baseweb="tab"] {
    background: transparent !important;
    color: rgba(0, 0, 0, 0.54) !important;
    -webkit-text-fill-color: rgba(0, 0, 0, 0.54) !important;
    font-size: var(--text-body-sm);
    font-weight: 500;
    border: 0 !important;
    border-radius: var(--radius-buttons) var(--radius-buttons) 0 0;
    padding: var(--spacing-12) var(--spacing-16);
    transition: color 200ms ease, background-color 200ms ease;
    box-shadow: none !important;
}

[data-testid="stTabs"] button[role="tab"] *,
[data-baseweb="tab"] * {
    color: inherit !important;
    -webkit-text-fill-color: inherit !important;
}

[data-testid="stTabs"] button[role="tab"]:hover,
[data-baseweb="tab"]:hover {
    color: var(--color-ink-black) !important;
    -webkit-text-fill-color: var(--color-ink-black) !important;
    background: rgba(255, 255, 255, 0.55) !important;
}

[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
[aria-selected="true"][data-baseweb="tab"] {
    background: var(--color-sky-tint) !important;
    color: var(--color-notion-blue) !important;
    -webkit-text-fill-color: var(--color-notion-blue) !important;
}

[data-baseweb="tab-highlight"] {
    background-color: var(--color-notion-blue) !important;
    height: 2px !important;
}

[data-baseweb="tab-border"] {
    background-color: var(--hairline) !important;
}

[data-testid="stAlert"] {
    border: 0 !important;
    border-radius: var(--radius-cards) !important;
    box-shadow: none !important;
}

a {
    color: var(--color-notion-blue) !important;
    text-decoration: none !important;
}

a:hover { text-decoration: underline !important; }

@media (max-width: 768px) {
    .main .block-container { padding: var(--spacing-16); }
    .kh-header { padding: var(--spacing-16); }
    .kh-title { font-size: 40px; letter-spacing: -1.2px; }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        transition-duration: 0.01ms !important;
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
"""


def safe_rerun() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()


def viewer_name(session) -> str:
    try:
        user = getattr(st, "user", None)
        for attribute in ("user_name", "email"):
            value = str(getattr(user, attribute, "") or "").strip()
            if value and value.lower() not in {"none", "null", "unknown"}:
                return value
    except Exception:
        pass
    fallback = str(
        scalar(session, "SELECT CURRENT_USER()", default="") or ""
    ).strip()
    if fallback and fallback.lower() not in {"none", "null", "unknown"}:
        return fallback
    return "Snowflake user"


def render_header(viewer: str) -> None:
    st.markdown(
        f"""
        <div class="kh-header">
            <div class="kh-mark-row" aria-hidden="true">
                <span class="kh-mark"></span>
                <span class="kh-mark"></span>
                <span class="kh-mark"></span>
                <span class="kh-mark"></span>
            </div>
            <div class="kh-title">Find <span class="kh-highlight">trusted</span> knowledge.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def collection_options(rows: list[dict[str, Any]]) -> tuple[list[str], dict[str, str]]:
    labels: list[str] = []
    mapping: dict[str, str] = {}
    for row in rows:
        label = f"{row['COLLECTION_NAME']} · {row['COLLECTION_ID']}"
        labels.append(label)
        mapping[label] = str(row["COLLECTION_ID"])
    return labels, mapping


def page_range_label(page_from: Any, page_to: Any) -> str:
    if page_from is None:
        return "Page unavailable"
    if page_to is None or int(page_from) == int(page_to):
        return f"Page {int(page_from)}"
    return f"Pages {int(page_from)}\u2013{int(page_to)}"


def render_source_card(source: dict[str, Any], index: int, session) -> None:
    title = html.escape(str(source.get("TITLE") or "Untitled document"))
    section = html.escape(str(source.get("SECTION_PATH") or "No section"))
    body = html.escape(str(source.get("CHUNK_TEXT") or ""))
    meta = " · ".join(
        part
        for part in [
            f"Source {index}",
            page_range_label(source.get("PAGE_FROM"), source.get("PAGE_TO")),
            "Visual evidence" if str(source.get("EVIDENCE_TYPE") or "TEXT") == "IMAGE" else "Text evidence",
            str(source.get("DOCUMENT_TYPE") or ""),
            str(source.get("LANGUAGE") or ""),
            section,
        ]
        if part
    )
    st.markdown(
        f"""
        <div class="kh-card">
            <div class="kh-card-title">{title}</div>
            <div class="kh-card-meta">{html.escape(meta)}</div>
            <div class="kh-card-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    image_path = str(source.get("IMAGE_STAGE_RELATIVE_PATH") or "")
    if image_path:
        image_bytes = read_staged_file_bytes(session, image_path)
        if image_bytes:
            st.image(image_bytes, width=480)
        else:
            st.warning("The visual evidence file could not be loaded from Snowflake.")
    path = str(source.get("STAGE_RELATIVE_PATH") or "")
    if path:
        url = create_scoped_file_url(session, path)
        if url:
            st.markdown(f"[Open original document]({url})")


def render_ask_tab(session, viewer: str) -> None:
    collections = list_accessible_collections(session, viewer, "READ")
    if not collections:
        st.error("You do not have READ access to any PFIZER ANTIINF collection.")
        return

    labels, mapping = collection_options(collections)
    library = list_library(session, viewer)
    doc_types = sorted({str(row.get("DOCUMENT_TYPE")) for row in library if row.get("DOCUMENT_TYPE")})
    languages = sorted({str(row.get("LANGUAGE")) for row in library if row.get("LANGUAGE")})

    with st.form("ask_knowledge_form"):
        with st.expander("Search settings", expanded=False):
            collection_label = st.selectbox("Collection", labels)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mode = st.selectbox("Mode", ["Grounded answer", "Search only"])
            with col2:
                document_type = st.selectbox("Document type", ["All"] + doc_types)
            with col3:
                language = st.selectbox("Language", ["All"] + languages)
            with col4:
                selected_model = st.selectbox(
                    "LLM model",
                    list(SUPPORTED_MODELS),
                    index=list(SUPPORTED_MODELS).index(DEFAULT_MODEL),
                    help="Used only when Mode is Grounded answer.",
                )
        question = st.text_area(
            "Question or search",
            placeholder="Ask a question about the approved knowledge base...",
            height=100,
        )
        submitted = st.form_submit_button("Search knowledge", type="primary")

    if not submitted:
        if not library:
            st.markdown(
                '<div class="kh-callout">No documents are searchable yet. A curator must upload, review, and publish the first document.</div>',
                unsafe_allow_html=True,
            )
        return
    if not question.strip():
        st.warning("Enter a question or search phrase.")
        return

    collection_id = mapping[collection_label]
    request_id = str(time.time_ns())
    overall_started = time.perf_counter()
    try:
        with st.spinner("Searching approved knowledge..."):
            chunks, search_latency = search_knowledge(
                session,
                query=question.strip(),
                collection_id=collection_id,
                viewer=viewer,
                document_type=document_type,
                language=language,
                limit=20,
            )
    except Exception as exc:
        st.error(f"Knowledge search failed: {exc}")
        log_event(
            session,
            event_type="SEARCH_ERROR",
            viewer=viewer,
            request_id=request_id,
            collection_id=collection_id,
            question=question,
            error={"type": type(exc).__name__, "message": str(exc)},
        )
        return

    filters = {
        "collection_id": collection_id,
        "document_type": document_type,
        "language": language,
        "mode": mode,
        "model": selected_model,
    }
    log_event(
        session,
        event_type="SEARCH",
        viewer=viewer,
        request_id=request_id,
        collection_id=collection_id,
        question=question,
        normalized_query=question.strip(),
        filters=filters,
        retrieved_chunk_ids=[str(row.get("CHUNK_ID")) for row in chunks],
        search_latency_ms=search_latency,
    )
    if not chunks:
        st.info("The approved index contains no matching evidence. Try a broader search or remove filters.")
        return

    if mode == "Grounded answer":
        try:
            with st.spinner("Generating a citation-validated answer..."):
                answer, generation_latency = generate_grounded_answer(
                    session,
                    question=question.strip(),
                    chunks=chunks,
                    model=selected_model,
                )
        except Exception as exc:
            st.error(f"Answer generation failed: {exc}")
            return
        total_latency = int((time.perf_counter() - overall_started) * 1000)
        sufficiency = "Evidence sufficient" if answer["evidence_sufficient"] else "Insufficient evidence"
        st.markdown(
            f"""
            <div class="kh-answer">
                <span class="kh-status">{html.escape(sufficiency)}</span>
                <div class="kh-card-body" style="margin-top:1rem">{html.escape(answer['answer'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if answer.get("conflicting_sources"):
            st.warning("The retrieved evidence contains conflicting sources. Review the cited passages.")
        if answer.get("missing_evidence"):
            with st.expander("Evidence gaps", expanded=not answer["evidence_sufficient"]):
                for gap in answer["missing_evidence"]:
                    st.write(f"- {gap}")
        answer_event_id = log_event(
            session,
            event_type="KNOWLEDGE_ANSWER",
            viewer=viewer,
            request_id=request_id,
            collection_id=collection_id,
            question=question,
            filters=filters,
            retrieved_chunk_ids=[str(row.get("CHUNK_ID")) for row in chunks],
            answer=answer["answer"],
            citations=answer["citations"],
            model=selected_model,
            search_latency_ms=search_latency,
            generation_latency_ms=generation_latency,
            total_latency_ms=total_latency,
        )
        st.session_state["last_answer_event_id"] = answer_event_id
        st.caption(
            f"Retrieved in {search_latency} ms · Generated in {generation_latency} ms · "
            f"{len(answer['citations'])} validated citations"
        )

    with st.expander(f"Retrieved evidence · {len(chunks)} passages", expanded=(mode == "Search only")):
        for index, source in enumerate(chunks, start=1):
            render_source_card(source, index, session)


def render_add_tab(session, viewer: str) -> None:
    collections = list_active_collections(session)
    if not collections:
        st.warning("No active PFIZER ANTIINF collection is available.")
        return
    labels, mapping = collection_options(collections)

    st.markdown(
        '<div class="kh-callout">Documents are parsed, visually analyzed, published, and checked for search readiness automatically. Visual issues are retained as recoverable warnings.</div>',
        unsafe_allow_html=True,
    )
    with st.form("add_knowledge_form"):
        collection_label = st.selectbox("Destination collection", labels)
        files = st.file_uploader(
            "Documents",
            type=["pdf", "docx", "pptx", "txt", "md"],
            accept_multiple_files=True,
            help="PDF, DOCX, PPTX, TXT, or Markdown. Maximum 100 MB per file.",
        )
        col1, col2 = st.columns(2)
        with col1:
            title_override = st.text_input("Title override", help="Applied only when uploading one file.")
            document_type = st.selectbox(
                "Document type",
                [
                    "Research publication",
                    "Clinical trial document",
                    "Policy",
                    "Manual",
                    "Contract",
                    "FAQ",
                    "Product information",
                    "Presentation",
                    "Report",
                    "Other",
                ],
            )
            language = st.selectbox("Language", ["English", "German", "French", "Spanish", "Other"])
        with col2:
            use_effective_dates = st.checkbox("Apply effective dates")
            effective_from = st.date_input("Effective from", value=date.today())
            effective_to = st.date_input("Effective to", value=date.today())
            tags_text = st.text_input("Tags", placeholder="clinical, policy, launch")
        business_id_text = st.text_area(
            "Business identifiers",
            placeholder='Optional JSON, for example {"PMID":"42437604","NCT_ID":"NCT00000000"}',
            height=80,
        )
        submitted = st.form_submit_button("Upload and process", type="primary")

    if not submitted:
        return
    if not files:
        st.warning("Choose at least one document.")
        return

    try:
        business_identifiers = json.loads(business_id_text) if business_id_text.strip() else {}
        if not isinstance(business_identifiers, dict):
            raise ValueError("Business identifiers must be a JSON object.")
    except ValueError as exc:
        st.error(f"Invalid business identifiers: {exc}")
        return

    collection_id = mapping[collection_label]
    collection = next(row for row in collections if row["COLLECTION_ID"] == collection_id)
    tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]
    successes: list[str] = []
    failures: list[str] = []
    progress = st.progress(0)
    for index, uploaded_file in enumerate(files, start=1):
        title = title_override.strip() if len(files) == 1 and title_override.strip() else uploaded_file.name
        try:
            upload, _content = register_upload(
                session,
                uploaded_file=uploaded_file,
                collection_id=collection_id,
                security_domain=str(collection["SECURITY_DOMAIN"]),
                title=title,
                language=language,
                document_type=document_type,
                effective_from=effective_from if use_effective_dates else None,
                effective_to=effective_to if use_effective_dates else None,
                viewer=viewer,
                tags=tags,
                business_identifiers=business_identifiers,
            )
            result = process_document(
                session,
                document_id=upload.document_id,
                version=upload.version,
                job_id=upload.job_id,
                viewer=viewer,
            )
            successes.append(
                f"{uploaded_file.name}: {result['pages']} pages, {result['images']} images, "
                f"{result['chunks']} chunks, {result['image_warnings']} visual warning(s), "
                f"status {result.get('status', 'INDEX_PENDING')}"
            )
        except DuplicateDocumentError as exc:
            failures.append(f"{uploaded_file.name}: {exc}")
        except Exception as exc:
            failures.append(f"{uploaded_file.name}: {type(exc).__name__}: {exc}")
        progress.progress(index / len(files))

    if successes:
        st.success(
            "Processing completed. Publication and Cortex Search readiness are handled automatically."
        )
        for message in successes:
            st.write(message)
    if failures:
        st.error("Some documents could not be processed.")
        for message in failures:
            st.write(message)


def render_library_tab(session, viewer: str) -> None:
    collections = list_accessible_collections(session, viewer, "READ")
    if not collections:
        st.error("You do not have access to a PFIZER ANTIINF collection.")
        return

    queued_jobs = list_queued_jobs(session, viewer)
    if queued_jobs:
        st.warning(f"{len(queued_jobs)} uploaded document(s) are waiting to be processed.")
        if st.button("Recover queued documents", type="primary", key="recover_queued_documents"):
            with st.spinner("Processing queued documents..."):
                recovery = recover_queued_jobs(session, viewer)
            succeeded = [row for row in recovery if row.get("SUCCESS")]
            failed = [row for row in recovery if not row.get("SUCCESS")]
            if succeeded:
                st.success(f"Recovered {len(succeeded)} queued document(s).")
            for row in failed:
                st.error(f"{row.get('TITLE')}: {row.get('ERROR')}")
            safe_rerun()

    labels, mapping = collection_options(collections)

    col1, col2 = st.columns(2)
    with col1:
        collection_label = st.selectbox("Collection filter", ["All"] + labels, key="library_collection")
    with col2:
        status = st.selectbox(
            "Status filter",
            [
                "All",
                "UPLOADED",
                "PARSING",
                "DRAFT_READY",
                "INDEX_PENDING",
                "READY",
                "READY_WITH_WARNINGS",
                "FAILED_PARSING",
                "FAILED_PAGE_MAPPING",
                "FAILED_CHUNKING",
                "FAILED_TOKEN_VALIDATION",
            ],
            key="library_status",
        )
    collection_id = mapping.get(collection_label, "All")
    documents = list_library(session, viewer, status=status, collection_id=collection_id)
    if not documents:
        st.info("No documents match the current library filters.")
        return

    display_columns = [
        "TITLE",
        "COLLECTION_NAME",
        "VERSION",
        "STATUS",
        "DOCUMENT_TYPE",
        "LANGUAGE",
        "PAGE_COUNT",
        "IMAGE_COUNT",
        "IMAGE_WARNING_COUNT",
        "CHUNK_COUNT",
        "UPLOADED_BY",
        "UPDATED_AT",
    ]
    frame = pd.DataFrame(documents)
    st.dataframe(frame[[column for column in display_columns if column in frame.columns]], use_container_width=True)

    choices: dict[str, dict[str, Any]] = {}
    for document in documents:
        label = (
            f"{document['TITLE']} · v{document['VERSION']} · {document['STATUS']} · "
            f"{str(document['DOCUMENT_ID'])[:8]}"
        )
        choices[label] = document
    selected_label = st.selectbox("Review document", list(choices), key="library_selected_document")
    selected = choices[selected_label]
    document_id = str(selected["DOCUMENT_ID"])
    version = int(selected["VERSION"])
    selected_collection = str(selected["COLLECTION_ID"])
    permissions = viewer_permissions(session, viewer, selected_collection)

    metric1, metric2, metric3, metric4, metric5, metric6 = st.columns(6)
    metric1.metric("Status", selected["STATUS"])
    metric2.metric("Pages", int(selected.get("PAGE_COUNT") or 0))
    metric3.metric("Images", int(selected.get("IMAGE_COUNT") or 0))
    metric4.metric("Visual warnings", int(selected.get("IMAGE_WARNING_COUNT") or 0))
    metric5.metric("Chunks", int(selected.get("CHUNK_COUNT") or 0))
    metric6.metric("Version", version)

    raw_warnings = selected.get("PROCESSING_WARNINGS") or []
    if isinstance(raw_warnings, str):
        try:
            raw_warnings = json.loads(raw_warnings)
        except ValueError:
            raw_warnings = [raw_warnings]
    if raw_warnings:
        with st.expander(f"Visual processing warnings · {len(raw_warnings)}", expanded=False):
            for warning in raw_warnings:
                st.write(f"- {warning}")

    action1, action2, action3 = st.columns(3)
    with action1:
        if selected["STATUS"] == "DRAFT_READY":
            st.info("Automatic publication is pending and will retry without user action.")
        elif selected["STATUS"] == "INDEX_PENDING":
            st.info("Cortex Search readiness is being checked automatically.")
        elif selected["STATUS"] == "READY_WITH_WARNINGS":
            st.warning("Text and available visual evidence are searchable; review the visual warnings above.")
    with action2:
        if selected["STATUS"] in {"READY", "READY_WITH_WARNINGS", "INDEX_PENDING"} and ({"PUBLISH", "ADMIN"} & permissions):
            if st.button("Unpublish", key=f"unpublish_{document_id}_{version}"):
                try:
                    unpublish_document(session, document_id, version, viewer)
                    st.success("Document removed from the published search corpus.")
                    safe_rerun()
                except Exception as exc:
                    st.error(str(exc))
    with action3:
        if {"UPLOAD", "ADMIN"} & permissions:
            if st.button("Reprocess", key=f"reprocess_{document_id}_{version}"):
                try:
                    with st.spinner("Reprocessing document..."):
                        result = reprocess_document(session, document_id, version, viewer)
                    st.success(
                        f"Reprocessed {result['pages']} pages and {result['images']} images "
                        f"into {result['chunks']} chunks."
                    )
                    safe_rerun()
                except Exception as exc:
                    st.error(str(exc))

    pages = get_document_pages(session, document_id, version)
    images = get_document_images(session, document_id, version)
    chunks = get_document_chunks(session, document_id, version)
    page_tab, image_tab, chunk_tab = st.tabs(["Parsed pages", "Extracted images", "Retrieval chunks"])
    with page_tab:
        if pages:
            page_numbers = [int(row["PAGE_NUMBER"]) for row in pages]
            page_number = st.selectbox("Page", page_numbers, key=f"page_{document_id}_{version}")
            page = next(row for row in pages if int(row["PAGE_NUMBER"]) == page_number)
            st.markdown(str(page.get("PAGE_MARKDOWN") or ""))
        else:
            st.info("No parsed pages are available.")
    with image_tab:
        if images:
            for image_row in images:
                label = (
                    f"Page {image_row['PAGE_NUMBER']} · {image_row.get('SOURCE_IMAGE_ID') or 'image'} · "
                    f"{image_row.get('ANALYSIS_STATUS')}"
                )
                with st.expander(label):
                    image_path = str(image_row.get("STAGE_RELATIVE_PATH") or "")
                    if image_path:
                        image_bytes = read_staged_file_bytes(session, image_path)
                        if image_bytes:
                            st.image(image_bytes, width=640)
                        else:
                            st.warning("The extracted image file could not be loaded from Snowflake.")
                    st.caption(
                        f"Type: {image_row.get('IMAGE_TYPE') or 'unknown'} · "
                        f"Information-bearing: {bool(image_row.get('IS_INFORMATION_BEARING'))} · "
                        f"Model: {image_row.get('MODEL') or 'not run'}"
                    )
                    if image_row.get("DESCRIPTION"):
                        st.write(image_row["DESCRIPTION"])
                    if image_row.get("EXTRACTED_TEXT"):
                        st.markdown("**Visible text**")
                        st.text(str(image_row["EXTRACTED_TEXT"]))
                    structured = image_row.get("STRUCTURED_CONTENT") or {}
                    if isinstance(structured, str):
                        try:
                            structured = json.loads(structured)
                        except ValueError:
                            structured = {}
                    facts = structured.get("facts") if isinstance(structured, dict) else []
                    if facts:
                        st.markdown("**Structured facts**")
                        for fact in facts:
                            st.write(f"- {fact}")
                    error_details = image_row.get("ERROR_DETAILS")
                    if isinstance(error_details, str):
                        try:
                            error_details = json.loads(error_details)
                        except ValueError:
                            error_details = error_details.strip()
                    if error_details not in (None, "", {}, []):
                        st.warning(f"Visual processing issue: {error_details}")
        else:
            st.info("No embedded images were extracted from this document.")
    with chunk_tab:
        if chunks:
            for chunk in chunks[:50]:
                label = (
                    f"Chunk {chunk['CHUNK_NUMBER']} · "
                    f"{page_range_label(chunk.get('PAGE_FROM'), chunk.get('PAGE_TO'))} · "
                    f"{chunk.get('SECTION_PATH') or 'No section'}"
                )
                with st.expander(label):
                    st.write(chunk.get("CHUNK_TEXT") or "")
                    st.caption(
                        f"Raw characters: {int(chunk.get('CHUNK_CHARACTER_COUNT') or 0)} · "
                        f"Search tokens: {int(chunk.get('SEARCH_TOKEN_COUNT') or 0)} · "
                        f"Strategy: {chunk.get('CHUNKING_STRATEGY') or 'legacy'} · "
                        f"Chunker: {chunk.get('CHUNKER_VERSION') or 'legacy'}"
                    )
                    if "ADMIN" in permissions:
                        quality_warnings: list[str] = []
                        token_count = int(chunk.get("SEARCH_TOKEN_COUNT") or 0)
                        character_count = int(chunk.get("CHUNK_CHARACTER_COUNT") or 0)
                        page_from = int(chunk.get("PAGE_FROM") or 0)
                        page_to = int(chunk.get("PAGE_TO") or page_from)
                        if token_count > 480:
                            quality_warnings.append(
                                "SEARCH_TEXT is above the preferred 480-token target."
                            )
                        if character_count and character_count < 350:
                            quality_warnings.append(
                                "Chunk is below the preferred 350-character merge threshold."
                            )
                        if page_from and page_to - page_from > 3:
                            quality_warnings.append(
                                "Chunk spans an unusually large page range."
                            )
                        if (
                            str(chunk.get("EVIDENCE_TYPE") or "TEXT") == "TEXT"
                            and not str(chunk.get("SECTION_PATH") or "").strip()
                        ):
                            quality_warnings.append("SECTION_PATH is missing.")
                        for warning in quality_warnings:
                            st.warning(warning)
                    st.caption(f"Chunk ID: {str(chunk.get('CHUNK_ID') or '')}")
        else:
            st.info("No retrieval chunks are available.")

    if "ADMIN" in permissions:
        st.markdown("#### Administrative deletion")
        confirmation = st.text_input(
            "Type the document ID to permanently delete this version",
            key=f"delete_confirm_{document_id}_{version}",
        )
        if st.button("Delete document and source file", key=f"delete_{document_id}_{version}"):
            if confirmation != document_id:
                st.error("The confirmation does not match the document ID.")
            else:
                try:
                    delete_document(session, document_id, version, viewer)
                    st.success("Document metadata, pages, images, chunks, job records, and staged files were deleted.")
                    safe_rerun()
                except Exception as exc:
                    st.error(str(exc))


def render_quality_tab(session, _viewer: str) -> None:
    summary = quality_summary(session)
    cols = st.columns(4)
    cols[0].metric("Documents", int(summary.get("DOCUMENTS") or 0))
    cols[1].metric("Ready", int(summary.get("READY_DOCUMENTS") or 0))
    cols[2].metric("Published chunks", int(summary.get("PUBLISHED_CHUNKS") or 0))
    cols[3].metric("Failed jobs", int(summary.get("FAILED_JOBS") or 0))
    image_cols = st.columns(3)
    image_cols[0].metric("Extracted images", int(summary.get("EXTRACTED_IMAGES") or 0))
    image_cols[1].metric("Information images", int(summary.get("INFORMATION_IMAGES") or 0))
    image_cols[2].metric("Visual warnings", int(summary.get("IMAGE_WARNINGS") or 0))
    st.markdown("#### Recent activity")
    events = recent_events(session, 100)
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True)
    else:
        st.info("No audit events have been recorded yet.")


def main() -> None:
    st.set_page_config(page_title="PFIZER ANTIINF Knowledge Hub", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    try:
        session = get_active_session()
        viewer = viewer_name(session)
        reconcile_automatic_lifecycle(session, viewer)
    except Exception as exc:
        st.error(f"PFIZER ANTIINF could not initialize its Snowflake session: {exc}")
        return

    render_header(viewer)
    ask_tab, add_tab, library_tab, quality_tab = st.tabs(
        ["Ask Knowledge", "Add Knowledge", "Knowledge Library", "Quality"]
    )
    with ask_tab:
        render_ask_tab(session, viewer)
    with add_tab:
        render_add_tab(session, viewer)
    with library_tab:
        render_library_tab(session, viewer)
    with quality_tab:
        render_quality_tab(session, viewer)


if __name__ == "__main__":
    main()
