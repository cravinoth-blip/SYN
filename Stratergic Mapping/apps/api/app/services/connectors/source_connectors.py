from __future__ import annotations

import asyncio
from datetime import date
from typing import Any
from urllib.parse import quote_plus
from xml.etree import ElementTree

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DocumentChunk, ParsedDocument, ProjectFile, SourceType
from app.services.connectors.base import SourceConnector, SourceEnvelope
from app.services.document_parser import chunk_text
from app.services.vector_store import index_external_source_chunks, search_external_source_chunks, search_project_chunks


settings = get_settings()
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


async def _get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    delay_seconds: float = 0.0,
) -> httpx.Response:
    for attempt in range(settings.external_request_retries + 1):
        if delay_seconds:
            await asyncio.sleep(delay_seconds)
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            is_retryable = exc.response.status_code in RETRYABLE_STATUS_CODES
            if not is_retryable or attempt >= settings.external_request_retries:
                raise
        except httpx.RequestError:
            if attempt >= settings.external_request_retries:
                raise

        await asyncio.sleep(delay_seconds + (2**attempt))

    raise RuntimeError("External request retry loop exhausted")


def _ncbi_params(db: str, query: str) -> str:
    params = f"db={db}&retmode=json&retmax={settings.ncbi_retmax}&term={query}"
    if settings.ncbi_email:
        params += f"&email={quote_plus(settings.ncbi_email)}"
    if settings.ncbi_api_key:
        params += f"&api_key={quote_plus(settings.ncbi_api_key)}"
    return params


def _ncbi_fetch_params(db: str, ids: list[str]) -> str:
    params = f"db={db}&retmode=xml&id={','.join(ids)}"
    if settings.ncbi_email:
        params += f"&email={quote_plus(settings.ncbi_email)}"
    if settings.ncbi_api_key:
        params += f"&api_key={quote_plus(settings.ncbi_api_key)}"
    return params


def _node_text(node: ElementTree.Element | None) -> str:
    if node is None:
        return ""
    return " ".join(" ".join(node.itertext()).split())


def _first_text(root: ElementTree.Element, path: str) -> str:
    return _node_text(root.find(path))


def _pubmed_abstract(article: ElementTree.Element) -> str:
    parts = []
    for abstract_text in article.findall(".//Abstract/AbstractText"):
        label = abstract_text.attrib.get("Label")
        text = _node_text(abstract_text)
        if text:
            parts.append(f"{label}: {text}" if label else text)
    return "\n\n".join(parts)


def _pubmed_year(article: ElementTree.Element) -> str:
    return (
        _first_text(article, ".//JournalIssue/PubDate/Year")
        or _first_text(article, ".//ArticleDate/Year")
        or _first_text(article, ".//JournalIssue/PubDate/MedlineDate")
    )


def _pubmed_authors(article: ElementTree.Element) -> list[str]:
    authors = []
    for author in article.findall(".//AuthorList/Author"):
        collective = _first_text(author, "CollectiveName")
        if collective:
            authors.append(collective)
            continue
        last = _first_text(author, "LastName")
        initials = _first_text(author, "Initials")
        if last:
            authors.append(f"{last} {initials}".strip())
    return authors


def _format_citation(authors: list[str], title: str, journal: str, year: str, identifier: str) -> str:
    author_text = ", ".join(authors[:3])
    if len(authors) > 3:
        author_text += ", et al."
    if not author_text:
        author_text = "Unknown authors"
    pieces = [author_text, title, journal, year, identifier]
    return ". ".join(piece for piece in pieces if piece) + "."


def _parse_pubmed_xml(xml_text: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(xml_text)
    records = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _first_text(article, ".//MedlineCitation/PMID")
        title = _first_text(article, ".//ArticleTitle") or f"PubMed record {pmid}"
        journal = _first_text(article, ".//Journal/Title") or _first_text(article, ".//Journal/ISOAbbreviation")
        year = _pubmed_year(article)
        abstract = _pubmed_abstract(article)
        authors = _pubmed_authors(article)
        doi = ""
        for article_id in article.findall(".//ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = _node_text(article_id)
                break
        records.append(
            {
                "id": pmid,
                "title": title,
                "journal": journal,
                "year": year,
                "authors": authors,
                "doi": doi,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
                "citation": _format_citation(authors, title, journal, year, f"PMID: {pmid}" if pmid else ""),
                "text": abstract,
                "raw_payload": {
                    "pmid": pmid,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "authors": authors,
                    "doi": doi,
                    "abstract": abstract,
                },
            }
        )
    return records


def _parse_pmc_xml(xml_text: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(xml_text)
    records = []
    for article in root.findall(".//article"):
        pmc_id = ""
        pmid = ""
        doi = ""
        for article_id in article.findall(".//article-id"):
            id_type = article_id.attrib.get("pub-id-type")
            value = _node_text(article_id)
            if id_type == "pmc":
                pmc_id = value.replace("PMC", "")
            elif id_type == "pmid":
                pmid = value
            elif id_type == "doi":
                doi = value
        title = _first_text(article, ".//article-title") or f"PMC record {pmc_id or pmid}"
        journal = _first_text(article, ".//journal-title") or _first_text(article, ".//journal-id")
        year = _first_text(article, ".//pub-date/year")
        authors = []
        for contributor in article.findall(".//contrib[@contrib-type='author']"):
            surname = _first_text(contributor, ".//surname")
            given_names = _first_text(contributor, ".//given-names")
            if surname:
                authors.append(f"{surname} {given_names}".strip())
        abstract = _node_text(article.find(".//abstract"))
        body = _node_text(article.find(".//body"))
        full_text = "\n\n".join(part for part in [abstract, body] if part)
        identifier = f"PMCID: PMC{pmc_id}" if pmc_id else f"PMID: {pmid}" if pmid else ""
        records.append(
            {
                "id": pmc_id or pmid or doi or title,
                "title": title,
                "journal": journal,
                "year": year,
                "authors": authors,
                "doi": doi,
                "pmid": pmid,
                "url": f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmc_id}/" if pmc_id else None,
                "citation": _format_citation(authors, title, journal, year, identifier),
                "text": full_text,
                "raw_payload": {
                    "pmc_id": pmc_id,
                    "pmid": pmid,
                    "doi": doi,
                    "title": title,
                    "journal": journal,
                    "year": year,
                    "authors": authors,
                    "abstract": abstract,
                    "full_text_chars": len(full_text),
                },
            }
        )
    return records


def _section_query(plan: dict[str, Any]) -> str:
    return " ".join(
        part
        for part in [
            plan.get("disease"),
            plan.get("subtype_biomarker"),
            plan.get("line_of_therapy"),
            plan.get("section_name"),
            plan.get("section_guidance"),
            plan.get("optional_brief"),
            plan.get("change_instruction"),
        ]
        if part
    )


def _envelopes_from_ranked_chunks(
    *,
    plan: dict[str, Any],
    source_type: str,
    records: list[dict[str, Any]],
) -> list[SourceEnvelope]:
    query = _section_query(plan)
    section_name = plan["section_name"]
    for record in records:
        chunks = chunk_text(record["text"])
        if not chunks:
            continue
        try:
            index_external_source_chunks(
                project_id=plan["project_id"],
                section_name=section_name,
                source_type=source_type,
                source_id=record["id"],
                source_title=record["title"],
                source_url=record["url"],
                citation=record["citation"],
                chunks=chunks,
            )
        except Exception:
            continue

    ranked = search_external_source_chunks(
        project_id=plan["project_id"],
        source_type=source_type,
        section_name=section_name,
        query=query,
        top_k=settings.ncbi_retmax,
    )
    if ranked:
        return [
            SourceEnvelope(
                source_title=match.filename,
                source_type=source_type,
                source_date=None,
                url=match.metadata.get("source_url") or None,
                geography=plan.get("geography"),
                raw_payload={
                    "source_id": match.file_id,
                    "chunk_id": match.chunk_id,
                    "semantic_score": match.score,
                    "distance": match.distance,
                    "citation": match.metadata.get("citation"),
                },
                extracted_summary=match.text[:1800],
                candidate_section=section_name,
                provenance={
                    "source_id": match.file_id,
                    "chunk_index": match.chunk_index,
                    "retrieval": "chroma_cosine",
                    "semantic_score": match.score,
                },
            )
            for match in ranked
        ]

    envelopes = []
    for record in records[: settings.ncbi_retmax]:
        if not record["text"]:
            continue
        envelopes.append(
            SourceEnvelope(
                source_title=record["title"],
                source_type=source_type,
                source_date=None,
                url=record["url"],
                geography=plan.get("geography"),
                raw_payload={**record["raw_payload"], "citation": record["citation"]},
                extracted_summary=record["text"][:1800],
                candidate_section=section_name,
                provenance={"source_id": record["id"], "retrieval": "xml_fallback"},
            )
        )
    return envelopes


class InternalUploadConnector(SourceConnector):
    source_type = SourceType.INTERNAL_UPLOAD.value

    def __init__(self, db: Session) -> None:
        self.db = db

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        project_id = plan["project_id"]
        section = plan["section_name"]
        query = " ".join(
            part
            for part in [
                plan.get("disease"),
                plan.get("subtype_biomarker"),
                plan.get("line_of_therapy"),
                section,
                plan.get("section_guidance"),
                plan.get("optional_brief"),
                plan.get("change_instruction"),
            ]
            if part
        )
        vector_matches = search_project_chunks(
            project_id=project_id,
            query=query,
            top_k=settings.internal_upload_top_k,
            excluded_document_ids=plan.get("excluded_document_ids") or [],
        )
        if vector_matches:
            envelopes: list[SourceEnvelope] = []
            for match in vector_matches:
                envelopes.append(
                    SourceEnvelope(
                        source_title=match.filename,
                        source_type=self.source_type,
                        source_date=None,
                        url=None,
                        geography=plan.get("geography"),
                        raw_payload={
                            "file_id": match.file_id,
                            "chunk_id": match.chunk_id,
                            "semantic_score": match.score,
                            "distance": match.distance,
                        },
                        extracted_summary=match.text[:900],
                        candidate_section=section,
                        provenance={
                            "project_file_id": match.file_id,
                            "chunk_index": match.chunk_index,
                            "retrieval": "chroma_cosine",
                            "semantic_score": match.score,
                        },
                    )
                )
            return envelopes

        excluded_document_ids = set(plan.get("excluded_document_ids") or [])
        statement = (
            select(ProjectFile, ParsedDocument, DocumentChunk)
            .join(ParsedDocument, ParsedDocument.file_id == ProjectFile.file_id)
            .join(DocumentChunk, DocumentChunk.parsed_document_id == ParsedDocument.parsed_document_id)
            .where(ProjectFile.project_id == project_id)
            .limit(settings.internal_upload_top_k)
        )
        envelopes: list[SourceEnvelope] = []
        for file, _parsed, chunk in self.db.execute(statement):
            if str(file.file_id) in excluded_document_ids:
                continue
            envelopes.append(
                SourceEnvelope(
                    source_title=file.filename,
                    source_type=self.source_type,
                    source_date=file.uploaded_at.date(),
                    url=None,
                    geography=plan.get("geography"),
                    raw_payload={"file_id": str(file.file_id), "chunk_id": str(chunk.chunk_id)},
                    extracted_summary=chunk.chunk_text[:900],
                    candidate_section=section,
                    provenance={
                        "project_file_id": str(file.file_id),
                        "chunk_index": chunk.chunk_index,
                        "retrieval": "sql_fallback",
                    },
                )
            )
        return envelopes


class PubMedConnector(SourceConnector):
    source_type = SourceType.PUBMED.value

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        query = quote_plus(f'{plan["disease"]} {plan.get("subtype_biomarker") or ""} {plan["section_name"]}')
        if not settings.live_connectors_enabled:
            return [
                SourceEnvelope(
                    source_title="PubMed connector configured query",
                    source_type=self.source_type,
                    source_date=date.today(),
                    url=None,
                    geography=plan.get("geography"),
                    raw_payload={
                        "query": query,
                        "retmax": settings.ncbi_retmax,
                        "status": "live_connectors_disabled",
                    },
                    extracted_summary=(
                        "PubMed retrieval is implemented and can run against NCBI E-utilities "
                        "when LIVE_CONNECTORS_ENABLED=true."
                    ),
                    candidate_section=plan["section_name"],
                    provenance={"connector": self.source_type, "requires": "LIVE_CONNECTORS_ENABLED"},
                )
            ]
        params = _ncbi_params("pubmed", query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
        async with httpx.AsyncClient(timeout=settings.external_request_timeout_seconds) as client:
            search = await _get_with_retries(
                client,
                search_url,
                delay_seconds=settings.ncbi_request_delay_seconds,
            )
            ids = search.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            fetch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                f"{_ncbi_fetch_params('pubmed', ids)}"
            )
            fetched = await _get_with_retries(
                client,
                fetch_url,
                delay_seconds=settings.ncbi_request_delay_seconds,
            )
        records = [record for record in _parse_pubmed_xml(fetched.text) if record["text"]]
        return _envelopes_from_ranked_chunks(
            plan=plan,
            source_type=self.source_type,
            records=records,
        )


class PMCConnector(SourceConnector):
    source_type = SourceType.PMC.value

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        query = quote_plus(f'{plan["disease"]} {plan.get("subtype_biomarker") or ""} {plan["section_name"]}')
        if not settings.live_connectors_enabled:
            return [
                SourceEnvelope(
                    source_title="PMC connector configured query",
                    source_type=self.source_type,
                    source_date=date.today(),
                    url=None,
                    geography=plan.get("geography"),
                    raw_payload={
                        "query": query,
                        "retmax": settings.ncbi_retmax,
                        "status": "live_connectors_disabled",
                    },
                    extracted_summary=(
                        "PMC full-text retrieval is implemented and can run against NCBI E-utilities "
                        "when LIVE_CONNECTORS_ENABLED=true."
                    ),
                    candidate_section=plan["section_name"],
                    provenance={"connector": self.source_type, "requires": "LIVE_CONNECTORS_ENABLED"},
                )
            ]

        params = _ncbi_params("pmc", query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}"
        async with httpx.AsyncClient(timeout=settings.external_request_timeout_seconds) as client:
            search = await _get_with_retries(
                client,
                search_url,
                delay_seconds=settings.ncbi_request_delay_seconds,
            )
            ids = search.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []
            fetch_url = (
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?"
                f"{_ncbi_fetch_params('pmc', ids)}"
            )
            fetched = await _get_with_retries(
                client,
                fetch_url,
                delay_seconds=settings.ncbi_request_delay_seconds,
            )

        records = [record for record in _parse_pmc_xml(fetched.text) if record["text"]]
        return _envelopes_from_ranked_chunks(
            plan=plan,
            source_type=self.source_type,
            records=records,
        )


class ClinicalTrialsConnector(SourceConnector):
    source_type = SourceType.CLINICAL_TRIALS.value

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        query = quote_plus(f'{plan["disease"]} {plan.get("subtype_biomarker") or ""}')
        if not settings.live_connectors_enabled:
            return [
                SourceEnvelope(
                    source_title="ClinicalTrials connector configured query",
                    source_type=self.source_type,
                    source_date=date.today(),
                    url=None,
                    geography=plan.get("geography"),
                    raw_payload={
                        "query": query,
                        "page_size": settings.clinical_trials_page_size,
                        "status": "live_connectors_disabled",
                    },
                    extracted_summary=(
                        "ClinicalTrials.gov v2 retrieval is implemented and can run when "
                        "LIVE_CONNECTORS_ENABLED=true."
                    ),
                    candidate_section=plan["section_name"],
                    provenance={
                        "connector": self.source_type,
                        "requires": "LIVE_CONNECTORS_ENABLED",
                    },
                )
            ]
        url = (
            "https://clinicaltrials.gov/api/v2/studies?"
            f"query.term={query}&pageSize={settings.clinical_trials_page_size}"
        )
        async with httpx.AsyncClient(timeout=settings.external_request_timeout_seconds) as client:
            response = await _get_with_retries(
                client,
                url,
                delay_seconds=settings.web_request_delay_seconds,
            )
        studies = response.json().get("studies", [])
        envelopes: list[SourceEnvelope] = []
        for study in studies:
            protocol = study.get("protocolSection", {})
            identification = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            nct_id = identification.get("nctId")
            title = identification.get("briefTitle") or nct_id or "ClinicalTrials study"
            envelopes.append(
                SourceEnvelope(
                    source_title=title,
                    source_type=self.source_type,
                    source_date=None,
                    url=f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None,
                    geography=plan.get("geography"),
                    raw_payload=study,
                    extracted_summary=(
                        f"Clinical trial signal for {plan['section_name']}: {title}. "
                        f"Status: {status.get('overallStatus', 'unknown')}."
                    ),
                    candidate_section=plan["section_name"],
                    provenance={"nct_id": nct_id},
                )
            )
        return envelopes


class SearchBackedConnector(SourceConnector):
    def __init__(self, source_type: SourceType, site_query: str) -> None:
        self.source_type = source_type.value
        self.site_query = site_query

    async def retrieve(self, plan: dict[str, Any]) -> list[SourceEnvelope]:
        query = f'{plan["disease"]} {plan.get("subtype_biomarker") or ""} {plan["section_name"]} {self.site_query}'
        if not settings.bing_search_api_key:
            return [
                SourceEnvelope(
                    source_title=f"{self.source_type} connector configured query",
                    source_type=self.source_type,
                    source_date=date.today(),
                    url=None,
                    geography=plan.get("geography"),
                    raw_payload={
                        "query": query,
                        "target_results": settings.web_search_results_per_source,
                        "status": "api_key_required",
                    },
                    extracted_summary=(
                        f"{self.source_type} retrieval is configured for query '{query}'. "
                        "Set BING_SEARCH_API_KEY to retrieve live web evidence."
                    ),
                    candidate_section=plan["section_name"],
                    provenance={"connector": self.source_type, "requires": "BING_SEARCH_API_KEY"},
                )
            ]

        url = "https://api.bing.microsoft.com/v7.0/search"
        headers = {"Ocp-Apim-Subscription-Key": settings.bing_search_api_key}
        values: list[dict[str, Any]] = []
        remaining = settings.web_search_results_per_source
        offset = 0
        async with httpx.AsyncClient(timeout=settings.external_request_timeout_seconds) as client:
            while remaining > 0:
                count = min(50, remaining)
                response = await _get_with_retries(
                    client,
                    url,
                    params={"q": query, "count": count, "offset": offset},
                    headers=headers,
                    delay_seconds=settings.web_request_delay_seconds,
                )
                page_values = response.json().get("webPages", {}).get("value", [])
                if not page_values:
                    break
                values.extend(page_values)
                if len(page_values) < count:
                    break
                remaining -= len(page_values)
                offset += len(page_values)
        return [
            SourceEnvelope(
                source_title=item.get("name", f"{self.source_type} result"),
                source_type=self.source_type,
                source_date=None,
                url=item.get("url"),
                geography=plan.get("geography"),
                raw_payload=item,
                extracted_summary=item.get("snippet", ""),
                candidate_section=plan["section_name"],
                provenance={"connector": self.source_type, "query": query},
            )
            for item in values
        ]


def build_connectors(db: Session) -> list[SourceConnector]:
    return [
        InternalUploadConnector(db),
        PubMedConnector(),
        PMCConnector(),
        ClinicalTrialsConnector(),
        SearchBackedConnector(SourceType.GUIDELINE, "guideline clinical practice"),
        SearchBackedConnector(SourceType.REGULATORY, "FDA EMA regulatory label approval"),
        SearchBackedConnector(SourceType.HTA, "HTA NICE HAS IQWiG AIFA"),
        SearchBackedConnector(SourceType.EPIDEMIOLOGY, "epidemiology prevalence incidence"),
        SearchBackedConnector(SourceType.CONGRESS, "ASCO ESMO congress abstract"),
        SearchBackedConnector(SourceType.NEWS, "pharma news press release"),
        SearchBackedConnector(SourceType.ADVOCACY, "patient advocacy organization"),
    ]
