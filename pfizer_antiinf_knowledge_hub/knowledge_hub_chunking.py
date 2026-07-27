from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Any, Callable, Iterable, Sequence


DEFAULT_EMBEDDING_MODEL = "snowflake-arctic-embed-m-v1.5"
SUPPORTED_STRATEGIES = {"markdown_section_v2", "page_bounded"}
SUPPORTED_PAGE_POLICIES = {"page_aware", "page_bounded", "slide_bounded"}


class ChunkingError(ValueError):
    """Raised when configuration or final chunk validation is unsafe."""


@dataclass(frozen=True)
class ChunkingConfig:
    strategy: str = "markdown_section_v2"
    page_policy: str = "page_aware"
    max_raw_characters: int = 1800
    overlap_characters: int = 200
    minimum_merge_characters: int = 350
    preferred_search_text_tokens: int = 480
    maximum_search_text_tokens: int = 512
    chunker_version: str = "markdown_section_v2"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL

    def validate(self) -> "ChunkingConfig":
        if self.strategy not in SUPPORTED_STRATEGIES:
            raise ChunkingError(f"Unsupported chunking strategy: {self.strategy}")
        if self.page_policy not in SUPPORTED_PAGE_POLICIES:
            raise ChunkingError(f"Unsupported page policy: {self.page_policy}")
        numeric = {
            "max_raw_characters": self.max_raw_characters,
            "overlap_characters": self.overlap_characters,
            "minimum_merge_characters": self.minimum_merge_characters,
            "preferred_search_text_tokens": self.preferred_search_text_tokens,
            "maximum_search_text_tokens": self.maximum_search_text_tokens,
        }
        if any(value <= 0 for value in numeric.values()):
            raise ChunkingError("Chunking configuration values must be positive.")
        if not 150 <= self.overlap_characters <= 250:
            raise ChunkingError("overlap_characters must be between 150 and 250.")
        if self.overlap_characters >= self.max_raw_characters:
            raise ChunkingError("overlap_characters must be smaller than max_raw_characters.")
        if self.minimum_merge_characters >= self.max_raw_characters:
            raise ChunkingError(
                "minimum_merge_characters must be smaller than max_raw_characters."
            )
        if self.maximum_search_text_tokens < self.preferred_search_text_tokens:
            raise ChunkingError(
                "maximum_search_text_tokens must be at least preferred_search_text_tokens."
            )
        if not self.chunker_version.strip():
            raise ChunkingError("chunker_version is required.")
        if not self.embedding_model.strip():
            raise ChunkingError("embedding_model is required.")
        return self


@dataclass(frozen=True)
class PageContent:
    page_number: int
    markdown: str


@dataclass(frozen=True)
class PageSpan:
    page_number: int
    start_offset: int
    end_offset: int


@dataclass(frozen=True)
class SectionSpan:
    section_key: str
    section_path: str
    start_offset: int
    end_offset: int
    text: str


@dataclass(frozen=True)
class RawChunk:
    text: str
    section_key: str
    section_path: str
    start_offset: int
    end_offset: int
    kind: str = "prose"
    compact_metadata: bool = False


@dataclass(frozen=True)
class FinalChunk:
    chunk_text: str
    search_text: str
    page_from: int
    page_to: int
    section_path: str
    chunk_character_count: int
    search_character_count: int
    search_token_count: int
    chunking_strategy: str
    chunker_version: str


TokenCounter = Callable[[Sequence[str]], list[int]]
ProgressCallback = Callable[[str, dict[str, Any]], None]


def _as_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def resolve_chunking_config(
    ingestion_config: Any,
    *,
    document_type: str = "",
    extension: str = "",
) -> ChunkingConfig:
    root = _as_object(ingestion_config)
    nested = _as_object(root.get("chunking"))
    values: dict[str, Any] = dict(nested)

    # Backward compatibility with the original flat collection configuration.
    if "max_raw_characters" not in values and root.get("target_chunk_chars") is not None:
        values["max_raw_characters"] = root["target_chunk_chars"]
    if "overlap_characters" not in values and root.get("overlap_chars") is not None:
        values["overlap_characters"] = root["overlap_chars"]

    overrides = _as_object(root.get("document_type_overrides"))
    type_key = document_type.strip().lower()
    if type_key and isinstance(overrides.get(type_key), dict):
        values.update(overrides[type_key])

    if type_key == "presentation" or extension.lower().lstrip(".") == "pptx":
        values["page_policy"] = values.get("presentation_page_policy", "slide_bounded")

    allowed = set(ChunkingConfig.__dataclass_fields__)
    converted = {key: value for key, value in values.items() if key in allowed}
    integer_fields = {
        "max_raw_characters",
        "overlap_characters",
        "minimum_merge_characters",
        "preferred_search_text_tokens",
        "maximum_search_text_tokens",
    }
    for key in integer_fields & converted.keys():
        try:
            converted[key] = int(converted[key])
        except (TypeError, ValueError) as exc:
            raise ChunkingError(f"{key} must be an integer.") from exc
    return ChunkingConfig(**converted).validate()


def normalize_markdown(value: str) -> str:
    return re.sub(r"\n{4,}", "\n\n\n", (value or "").replace("\r\n", "\n").replace("\r", "\n")).strip()


def build_document_stream(pages: Iterable[PageContent]) -> tuple[str, list[PageSpan]]:
    parts: list[str] = []
    page_map: list[PageSpan] = []
    offset = 0
    for page in sorted(pages, key=lambda item: item.page_number):
        text = normalize_markdown(page.markdown)
        if not text:
            continue
        if parts:
            parts.append("\n\n")
            offset += 2
        start = offset
        parts.append(text)
        offset += len(text)
        page_map.append(PageSpan(page.page_number, start, offset))
    return "".join(parts), page_map


def _meaningful_section_body(text: str) -> bool:
    without_heading = re.sub(r"^#{1,6}\s+[^\n]+\n?", "", text.strip(), count=1)
    return bool(without_heading.strip())


def _markdown_sections(stream: str, *, document_type: str = "") -> list[SectionSpan]:
    headings = list(re.finditer(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$", stream))
    if not headings:
        lowered_type = document_type.strip().lower()
        if lowered_type == "contract":
            headings = list(
                re.finditer(
                    r"(?mi)^((?:clause\s+)?\d+(?:\.\d+)+)[ \t]+(.+?)[ \t]*$",
                    stream,
                )
            )
        elif lowered_type in {"faq", "frequently asked questions"}:
            headings = list(re.finditer(r"(?mi)^(Q(?:uestion)?\s*[:.]\s*.+?)$", stream))

    if not headings:
        return [SectionSpan("section-0", "", 0, len(stream), stream)] if stream.strip() else []

    sections: list[SectionSpan] = []
    if headings[0].start() > 0 and stream[: headings[0].start()].strip():
        text = stream[: headings[0].start()].strip()
        start = stream.find(text, 0, headings[0].start())
        sections.append(SectionSpan("section-preamble", "", start, start + len(text), text))

    stack: dict[int, str] = {}
    markdown_headings = headings[0].group(0).lstrip().startswith("#")
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(stream)
        if markdown_headings:
            level = len(heading.group(1))
            label = heading.group(2).strip()
            stack[level] = label
            for old_level in list(stack):
                if old_level > level:
                    stack.pop(old_level, None)
            path = " > ".join(stack[key] for key in sorted(stack))
        else:
            path = " ".join(group for group in heading.groups() if group).strip()
        raw = stream[heading.start() : end]
        text = raw.strip()
        if not text:
            continue
        start = heading.start() + raw.find(text)
        if markdown_headings and not _meaningful_section_body(text):
            continue
        sections.append(
            SectionSpan(f"section-{index}", path, start, start + len(text), text)
        )
    return sections


def identify_sections(
    stream: str,
    page_map: Sequence[PageSpan],
    *,
    page_policy: str,
    document_type: str = "",
) -> list[SectionSpan]:
    if page_policy == "page_aware":
        return _markdown_sections(stream, document_type=document_type)

    sections: list[SectionSpan] = []
    for page in page_map:
        page_text = stream[page.start_offset : page.end_offset]
        for inner_index, section in enumerate(
            _markdown_sections(page_text, document_type=document_type)
        ):
            sections.append(
                replace(
                    section,
                    section_key=f"page-{page.page_number}-section-{inner_index}",
                    start_offset=section.start_offset + page.start_offset,
                    end_offset=section.end_offset + page.start_offset,
                )
            )
    return sections


@dataclass(frozen=True)
class _Block:
    text: str
    start_offset: int
    end_offset: int
    kind: str


def _trim_block(text: str, start: int, kind: str) -> _Block | None:
    stripped = text.strip()
    if not stripped:
        return None
    relative = text.find(stripped)
    absolute = start + relative
    return _Block(stripped, absolute, absolute + len(stripped), kind)


def _is_table_start(lines: Sequence[tuple[str, int, int]], index: int) -> bool:
    if index + 1 >= len(lines) or "|" not in lines[index][0]:
        return False
    separator = lines[index + 1][0].strip()
    return bool(
        re.match(r"^\|?\s*:?-{3,}(?:\s*\|\s*:?-{3,})+\s*\|?$", separator)
    )


def _blocks(section: SectionSpan) -> list[_Block]:
    lines: list[tuple[str, int, int]] = []
    cursor = 0
    for raw in section.text.splitlines(keepends=True):
        content = raw.rstrip("\n")
        lines.append((content, section.start_offset + cursor, section.start_offset + cursor + len(content)))
        cursor += len(raw)
    if cursor < len(section.text):
        content = section.text[cursor:]
        lines.append((content, section.start_offset + cursor, section.end_offset))

    output: list[_Block] = []
    index = 0
    while index < len(lines):
        line, start, _end = lines[index]
        if not line.strip():
            index += 1
            continue
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence = stripped[:3]
            end_index = index + 1
            while end_index < len(lines):
                if lines[end_index][0].lstrip().startswith(fence):
                    end_index += 1
                    break
                end_index += 1
            raw = "\n".join(item[0] for item in lines[index:end_index])
            block = _trim_block(raw, start, "code")
            if block:
                output.append(block)
            index = end_index
            continue
        if _is_table_start(lines, index):
            end_index = index + 2
            while end_index < len(lines) and "|" in lines[end_index][0] and lines[end_index][0].strip():
                end_index += 1
            raw = "\n".join(item[0] for item in lines[index:end_index])
            block = _trim_block(raw, start, "table")
            if block:
                output.append(block)
            index = end_index
            continue

        end_index = index + 1
        while end_index < len(lines):
            if not lines[end_index][0].strip() or _is_table_start(lines, end_index):
                break
            next_line = lines[end_index][0].lstrip()
            if next_line.startswith("```") or next_line.startswith("~~~"):
                break
            end_index += 1
        raw = "\n".join(item[0] for item in lines[index:end_index])
        block = _trim_block(raw, start, "prose")
        if block:
            output.append(block)
        index = end_index
    return output


def _semantic_cut(text: str, maximum: int) -> int:
    if len(text) <= maximum:
        return len(text)
    minimum = max(1, int(maximum * 0.45))
    window = text[: maximum + 1]
    boundary_patterns = (
        r"\n\n+",
        r"(?<=[.!?])\s+",
        r"\n",
        r"\s+",
    )
    for pattern in boundary_patterns:
        positions = [match.end() for match in re.finditer(pattern, window)]
        safe = [position for position in positions if minimum <= position <= maximum]
        if safe:
            return safe[-1]
    return maximum


def _split_plain_block(block: _Block, maximum: int) -> list[_Block]:
    pieces: list[_Block] = []
    cursor = 0
    while cursor < len(block.text):
        remaining = block.text[cursor:]
        cut = _semantic_cut(remaining, maximum)
        raw = remaining[:cut]
        piece = _trim_block(raw, block.start_offset + cursor, block.kind)
        if piece:
            pieces.append(piece)
        cursor += max(cut, 1)
        while cursor < len(block.text) and block.text[cursor].isspace():
            cursor += 1
    return pieces


def _split_table_block(block: _Block, maximum: int) -> list[_Block]:
    lines = block.text.splitlines()
    if len(lines) < 3:
        return _split_plain_block(block, maximum)
    header = "\n".join(lines[:2]).strip()
    rows = lines[2:]
    if len(header) + 1 >= maximum:
        return _split_plain_block(block, maximum)
    output: list[_Block] = []
    group: list[str] = []
    search_from = 0
    for row in rows:
        candidate = "\n".join([header, *group, row]).strip()
        if group and len(candidate) > maximum:
            text = "\n".join([header, *group]).strip()
            last_row = group[-1]
            end_at = block.text.find(last_row, search_from) + len(last_row)
            output.append(_Block(text, block.start_offset, block.start_offset + max(end_at, len(header)), "table"))
            search_from = max(end_at, search_from)
            group = []
        if len("\n".join([header, row])) > maximum:
            row_start = block.text.find(row, search_from)
            row_block = _Block(
                row,
                block.start_offset + max(row_start, 0),
                block.start_offset + max(row_start, 0) + len(row),
                "table",
            )
            output.extend(_split_plain_block(row_block, maximum - len(header) - 1))
            group = []
        else:
            group.append(row)
    if group:
        text = "\n".join([header, *group]).strip()
        last_row = group[-1]
        end_at = block.text.rfind(last_row) + len(last_row)
        output.append(_Block(text, block.start_offset, block.start_offset + max(end_at, len(header)), "table"))
    return output


def _split_code_block(block: _Block, maximum: int) -> list[_Block]:
    lines = block.text.splitlines()
    if len(lines) < 3:
        return _split_plain_block(block, maximum)
    opening = lines[0]
    closing = lines[-1] if lines[-1].lstrip().startswith(("```", "~~~")) else opening[:3]
    allowance = maximum - len(opening) - len(closing) - 2
    if allowance < 40:
        return _split_plain_block(block, maximum)
    body = "\n".join(lines[1:-1])
    body_start = block.start_offset + block.text.find(lines[1]) if len(lines) > 2 else block.start_offset
    pieces = _split_plain_block(_Block(body, body_start, body_start + len(body), "code"), allowance)
    return [
        _Block(
            f"{opening}\n{piece.text}\n{closing}",
            piece.start_offset,
            piece.end_offset,
            "code",
        )
        for piece in pieces
    ]


def _split_block(block: _Block, maximum: int) -> list[_Block]:
    if len(block.text) <= maximum:
        return [block]
    if block.kind == "table":
        return _split_table_block(block, maximum)
    if block.kind == "code":
        return _split_code_block(block, maximum)
    return _split_plain_block(block, maximum)


def _pack_section(section: SectionSpan, maximum: int) -> list[RawChunk]:
    expanded: list[_Block] = []
    for block in _blocks(section):
        expanded.extend(_split_block(block, maximum))
    chunks: list[RawChunk] = []
    current: list[_Block] = []

    def emit() -> None:
        nonlocal current
        if not current:
            return
        text = "\n\n".join(item.text for item in current).strip()
        if text:
            kinds = {item.kind for item in current}
            chunks.append(
                RawChunk(
                    text=text,
                    section_key=section.section_key,
                    section_path=section.section_path,
                    start_offset=min(item.start_offset for item in current),
                    end_offset=max(item.end_offset for item in current),
                    kind=next(iter(kinds)) if len(kinds) == 1 else "mixed",
                )
            )
        current = []

    for block in expanded:
        candidate_length = len(block.text) + sum(len(item.text) + 2 for item in current)
        if current and candidate_length > maximum:
            emit()
        current.append(block)
    emit()
    return chunks


def _merge_small_chunks(chunks: list[RawChunk], config: ChunkingConfig) -> list[RawChunk]:
    merged = list(chunks)
    index = 0
    while index < len(merged):
        current = merged[index]
        if len(current.text) >= config.minimum_merge_characters:
            index += 1
            continue
        if index > 0 and merged[index - 1].section_key == current.section_key:
            previous = merged[index - 1]
            text = f"{previous.text}\n\n{current.text}".strip()
            if len(text) <= config.max_raw_characters:
                merged[index - 1] = replace(
                    previous,
                    text=text,
                    end_offset=max(previous.end_offset, current.end_offset),
                    kind=previous.kind if previous.kind == current.kind else "mixed",
                )
                merged.pop(index)
                continue
        if index + 1 < len(merged) and merged[index + 1].section_key == current.section_key:
            following = merged[index + 1]
            text = f"{current.text}\n\n{following.text}".strip()
            if len(text) <= config.max_raw_characters:
                merged[index] = replace(
                    current,
                    text=text,
                    end_offset=max(current.end_offset, following.end_offset),
                    kind=current.kind if current.kind == following.kind else "mixed",
                )
                merged.pop(index + 1)
                continue
        index += 1
    return merged


def _safe_overlap_suffix(text: str, maximum: int) -> str:
    if maximum <= 0 or not text:
        return ""
    tail = text[-maximum:]
    if len(text) <= maximum:
        return tail.strip()
    for pattern in (r"\n\n+", r"(?<=[.!?])\s+", r"\n", r"\s+"):
        match = re.search(pattern, tail)
        if match and match.end() < len(tail):
            return tail[match.end() :].strip()
    return ""


def _apply_overlap(chunks: list[RawChunk], config: ChunkingConfig) -> list[RawChunk]:
    output: list[RawChunk] = []
    for chunk in chunks:
        if output and output[-1].section_key == chunk.section_key:
            previous = output[-1]
            available = config.max_raw_characters - len(chunk.text) - 2
            overlap = _safe_overlap_suffix(
                previous.text,
                min(config.overlap_characters, max(0, available)),
            )
            if overlap and not chunk.text.startswith(overlap):
                chunk = replace(
                    chunk,
                    text=f"{overlap}\n\n{chunk.text}".strip(),
                    start_offset=min(chunk.start_offset, max(previous.start_offset, previous.end_offset - len(overlap))),
                )
        output.append(chunk)
    return output


def _page_range(chunk: RawChunk, page_map: Sequence[PageSpan]) -> tuple[int, int]:
    pages = [
        page.page_number
        for page in page_map
        if chunk.start_offset < page.end_offset and chunk.end_offset > page.start_offset
    ]
    if not pages:
        raise ChunkingError("A chunk could not be mapped to an authoritative page range.")
    return min(pages), max(pages)


def _date_text(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def _approved_tags(metadata: dict[str, Any]) -> list[str]:
    raw = metadata.get("effective_tags") or metadata.get("tags") or []
    if isinstance(raw, str):
        raw = [raw]
    tags: list[str] = []
    for value in raw if isinstance(raw, (list, tuple)) else []:
        tag = re.sub(r"[\r\n]+", " ", str(value)).strip()[:80]
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:20]


def build_search_text(
    metadata: dict[str, Any],
    chunk: RawChunk,
    page_from: int,
    page_to: int,
    *,
    compact: bool = False,
) -> str:
    lines = [f"Title: {str(metadata.get('title') or 'Untitled').strip()}"]
    document_type = str(metadata.get("document_type") or "").strip()
    if document_type:
        lines.append(f"Document type: {document_type}")
    evidence_type = str(metadata.get("evidence_type") or "").strip()
    if evidence_type and evidence_type.upper() != "TEXT":
        lines.append(f"Evidence type: {evidence_type}")
    image_id = str(metadata.get("image_id") or "").strip()
    if image_id:
        lines.append(f"Image ID: {image_id}")
    if not compact:
        effective_from = _date_text(metadata.get("effective_from"))
        effective_to = _date_text(metadata.get("effective_to"))
        if effective_from and effective_to and effective_from != effective_to:
            lines.append(f"Effective dates: {effective_from} to {effective_to}")
        elif effective_from:
            lines.append(f"Effective date: {effective_from}")
        tags = _approved_tags(metadata)
        if tags:
            lines.append(f"Topics: {', '.join(tags)}")
        language = str(metadata.get("language") or "").strip()
        if language:
            lines.append(f"Language: {language}")
    if chunk.section_path:
        lines.append(f"Section: {chunk.section_path}")
    lines.append(f"Pages: {page_from}" if page_from == page_to else f"Pages: {page_from}-{page_to}")
    lines.extend(["", chunk.text])
    return "\n".join(lines).strip()


def _split_for_token_limit(chunk: RawChunk, config: ChunkingConfig, token_count: int) -> list[RawChunk]:
    ratio_target = int(
        len(chunk.text) * config.preferred_search_text_tokens / max(token_count, 1)
    )
    target = min(config.max_raw_characters, max(80, ratio_target))
    if target >= len(chunk.text):
        target = max(40, len(chunk.text) // 2)
    block = _Block(chunk.text, chunk.start_offset, chunk.end_offset, chunk.kind)
    pieces = _split_block(block, target)
    if len(pieces) < 2:
        pieces = _split_plain_block(block, target)
    if len(pieces) < 2:
        raise ChunkingError(
            "SEARCH_TEXT exceeds the token maximum and cannot be split safely."
        )
    # The hard embedding limit takes precedence over overlap. Re-applying the full
    # configured overlap here can make a metadata-heavy chunk impossible to shrink.
    # The original semantic split already retains context inside the same section.
    return [
        RawChunk(
            text=piece.text,
            section_key=chunk.section_key,
            section_path=chunk.section_path,
            start_offset=piece.start_offset,
            end_offset=piece.end_offset,
            kind=piece.kind,
            compact_metadata=True,
        )
        for piece in pieces
        if piece.text.strip()
    ]


def _count(token_counter: TokenCounter, texts: Sequence[str]) -> list[int]:
    counts = token_counter(texts)
    if len(counts) != len(texts):
        raise ChunkingError("Token counter returned an unexpected number of results.")
    normalized: list[int] = []
    for value in counts:
        try:
            count = int(value)
        except (TypeError, ValueError) as exc:
            raise ChunkingError("Token counting failed for SEARCH_TEXT.") from exc
        if count < 0:
            raise ChunkingError("Token counting returned a negative value.")
        normalized.append(count)
    return normalized


def finalize_chunks(
    candidates: list[RawChunk],
    *,
    page_map: Sequence[PageSpan],
    metadata: dict[str, Any],
    config: ChunkingConfig,
    token_counter: TokenCounter,
    progress: ProgressCallback | None = None,
) -> list[FinalChunk]:
    working = [candidate for candidate in candidates if candidate.text.strip()]
    for iteration in range(20):
        ranges = [_page_range(candidate, page_map) for candidate in working]
        search_texts = [
            build_search_text(
                metadata,
                candidate,
                page_from,
                page_to,
                compact=candidate.compact_metadata,
            )
            for candidate, (page_from, page_to) in zip(working, ranges)
        ]
        if progress:
            progress("COUNTING_TOKENS", {"candidate_count": len(search_texts), "iteration": iteration + 1})
        counts = _count(token_counter, search_texts)
        overflow = [index for index, count in enumerate(counts) if count > config.maximum_search_text_tokens]
        if not overflow:
            final = [
                FinalChunk(
                    chunk_text=candidate.text,
                    search_text=search_text,
                    page_from=page_from,
                    page_to=page_to,
                    section_path=candidate.section_path,
                    chunk_character_count=len(candidate.text),
                    search_character_count=len(search_text),
                    search_token_count=count,
                    chunking_strategy=config.strategy,
                    chunker_version=config.chunker_version,
                )
                for candidate, search_text, (page_from, page_to), count in zip(
                    working, search_texts, ranges, counts
                )
            ]
            if progress:
                progress("VALIDATING_CHUNKS", {"chunk_count": len(final)})
            validate_final_chunks(final, config)
            return final

        replacement: list[RawChunk] = []
        overflow_set = set(overflow)
        for index, candidate in enumerate(working):
            if index not in overflow_set:
                replacement.append(candidate)
                continue
            if not candidate.compact_metadata:
                replacement.append(replace(candidate, compact_metadata=True))
                continue
            replacement.extend(_split_for_token_limit(candidate, config, counts[index]))
        working = replacement
    raise ChunkingError("Token-limit enforcement did not converge after 20 iterations.")


def validate_final_chunks(chunks: Sequence[FinalChunk], config: ChunkingConfig) -> None:
    if not chunks:
        raise ChunkingError("No non-empty chunks were produced.")
    for chunk in chunks:
        if not chunk.chunk_text.strip():
            raise ChunkingError("An empty chunk was produced.")
        if chunk.page_from > chunk.page_to:
            raise ChunkingError("A chunk has an invalid page range.")
        if chunk.search_token_count > config.maximum_search_text_tokens:
            raise ChunkingError(
                f"A chunk exceeds {config.maximum_search_text_tokens} SEARCH_TEXT tokens."
            )


def chunk_document(
    pages: Iterable[PageContent],
    *,
    metadata: dict[str, Any],
    config: ChunkingConfig,
    token_counter: TokenCounter,
    progress: ProgressCallback | None = None,
) -> list[FinalChunk]:
    config.validate()
    if progress:
        progress("BUILDING_PAGE_MAP", {})
    stream, page_map = build_document_stream(pages)
    if not stream or not page_map:
        raise ChunkingError("The document has no non-empty parsed pages.")
    if progress:
        progress("DETECTING_SECTIONS", {"page_count": len(page_map)})
    sections = identify_sections(
        stream,
        page_map,
        page_policy=config.page_policy,
        document_type=str(metadata.get("document_type") or ""),
    )
    candidates: list[RawChunk] = []
    for section in sections:
        candidates.extend(_pack_section(section, config.max_raw_characters))
    if progress:
        progress("CHUNKING", {"section_count": len(sections), "candidate_count": len(candidates)})
    candidates = _merge_small_chunks(candidates, config)
    if progress:
        progress("MERGING_SMALL_CHUNKS", {"candidate_count": len(candidates)})
    candidates = _apply_overlap(candidates, config)
    return finalize_chunks(
        candidates,
        page_map=page_map,
        metadata=metadata,
        config=config,
        token_counter=token_counter,
        progress=progress,
    )


def deterministic_chunk_id(
    *,
    document_id: str,
    version: int,
    chunker_version: str,
    section_path: str,
    chunk_sequence: int,
    chunk_text: str,
    evidence_key: str = "TEXT",
) -> str:
    content_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    identity = "|".join(
        [
            document_id,
            str(version),
            chunker_version,
            section_path,
            str(chunk_sequence),
            evidence_key,
            content_hash,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def approximate_token_counter(texts: Sequence[str]) -> list[int]:
    """Conservative local-only counter for tests; production uses AI_COUNT_TOKENS."""
    return [max(1, (len(text) + 2) // 3) for text in texts]


EXPERIMENT_CONFIGS = {
    "A": ChunkingConfig(
        strategy="page_bounded",
        page_policy="page_bounded",
        max_raw_characters=1800,
        overlap_characters=250,
        chunker_version="page_bounded_v1",
    ),
    "B": ChunkingConfig(
        max_raw_characters=1500,
        overlap_characters=200,
        chunker_version="markdown_section_v2_b",
    ),
    "C": ChunkingConfig(),
}
