"""
Audit Logger — Full provenance chain for every pipeline run.

Captures every tool call, retrieval result, code execution, and model
decision across all 4 passes. Outputs structured markdown and JSON files.
"""

import json
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Any, Optional

import config

# Maximum characters stored per tool input/output payload in audit records.
MAX_AUDIT_PAYLOAD_CHARS = 5_000

# Keys whose values are redacted before being written to disk.
_REDACT_TOKENS = {"key", "token", "password", "secret", "authorization", "passphrase"}


def _redact(obj: Any) -> Any:
    """Recursively redact sensitive-looking keys from dicts before persisting."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            if any(token in k.lower() for token in _REDACT_TOKENS):
                result[k] = "***REDACTED***"
            else:
                result[k] = _redact(v)
        return result
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj


def _dedupe_ordered(items: list[str]) -> list[str]:
    """Remove duplicates from a list while preserving original order."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


@dataclass
class AuditEntry:
    """Single logged event in the pipeline."""
    pass_number: int
    timestamp: str
    tool_name: str
    tool_input: dict
    tool_output_summary: str
    tool_output_full: Any = None      # capped at MAX_AUDIT_PAYLOAD_CHARS on save
    decision_note: Optional[str] = None   # concise operator/model justification
    duration_ms: Optional[int] = None
    error: Optional[str] = None


class AuditLogger:
    """Accumulates audit entries across all passes and renders them to markdown."""

    def __init__(self, disease: str, run_id: str):
        self.disease = disease
        self.run_id = run_id
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.entries: list[AuditEntry] = []
        self.pass_summaries: dict[int, dict] = {}

    def mark_complete(self) -> None:
        """Record the actual pipeline completion time."""
        self.end_time = datetime.now(timezone.utc)

    # ─── Logging ─────────────────────────────────────────────────────────────

    def log_tool_call(
        self,
        pass_number: int,
        tool_name: str,
        tool_input: dict,
        tool_output: Any,
        output_summary: str,
        decision_note: Optional[str] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            pass_number=pass_number,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tool_name=tool_name,
            tool_input=_redact(tool_input),
            tool_output_summary=output_summary,
            tool_output_full=_redact(tool_output),
            decision_note=decision_note,
            duration_ms=duration_ms,
            error=error,
        )
        self.entries.append(entry)
        return entry

    def log_pass_summary(
        self,
        pass_number: int,
        total_tool_calls: int,
        tools_used: list[str],
        key_decisions: list[str],
        output_summary: str,
    ) -> None:
        self.pass_summaries[pass_number] = {
            "total_tool_calls": total_tool_calls,
            "tools_used": _dedupe_ordered(tools_used),
            "key_decisions": key_decisions,
            "output_summary": output_summary,
        }

    # ─── Rendering ───────────────────────────────────────────────────────────

    def render_markdown(self) -> str:
        """Compile the full audit trail into structured markdown."""
        end_iso = (self.end_time or datetime.now(timezone.utc)).isoformat()
        lines = [
            "# Audit Trail — Patient Journey Pipeline",
            "",
            f"**Disease:** {self.disease}",
            f"**Run ID:** {self.run_id}",
            f"**Started:** {self.start_time.isoformat()}",
            f"**Completed:** {end_iso}",
            f"**Total tool calls:** {len(self.entries)}",
            "",
            "---",
            "",
        ]

        pass_names = {
            1: "Deep Generation",
            2: "Verification & Deepening",
            3: "Artifact Construction",
            4: "Editorial Polish",
        }

        for pass_num in range(1, 5):
            pass_entries = [e for e in self.entries if e.pass_number == pass_num]
            summary = self.pass_summaries.get(pass_num, {})

            lines.append(f"## Pass {pass_num} — {pass_names[pass_num]}")
            lines.append("")

            if summary:
                lines.append(f"**Tool calls:** {summary.get('total_tool_calls', len(pass_entries))}")
                lines.append(f"**Tools used:** {', '.join(summary.get('tools_used', []))}")
                lines.append("")
                if summary.get("key_decisions"):
                    lines.append("### Key decisions")
                    for d in summary["key_decisions"]:
                        lines.append(f"- {d}")
                    lines.append("")

            if pass_entries:
                lines.append("### Tool call log")
                lines.append("")
                for i, entry in enumerate(pass_entries, 1):
                    lines.append(f"#### Call {i}: `{entry.tool_name}`")
                    lines.append(f"- **Time:** {entry.timestamp}")
                    if entry.duration_ms is not None:
                        lines.append(f"- **Duration:** {entry.duration_ms}ms")
                    # Fenced block avoids backtick escaping issues
                    input_json = json.dumps(entry.tool_input, indent=2, default=str)[:1000]
                    lines.append("- **Input:**")
                    lines.append("```json")
                    lines.append(input_json)
                    lines.append("```")
                    lines.append(f"- **Output:** {entry.tool_output_summary}")
                    if entry.decision_note:
                        lines.append(f"- **Note:** {entry.decision_note}")
                    if entry.error:
                        lines.append(f"- **ERROR:** {entry.error}")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def save(self, output_dir: Optional[str] = None) -> str:
        """Write markdown audit trail to disk. Returns file path."""
        out_dir = output_dir or config.AUDIT_LOG_DIR
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"audit_{self.run_id}.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.render_markdown())
        except OSError as e:
            raise RuntimeError(f"Failed to write audit markdown to {path}: {e}") from e
        return path

    def save_raw_json(self, output_dir: Optional[str] = None) -> str:
        """Write full structured audit data as JSON (for programmatic use)."""
        out_dir = output_dir or config.AUDIT_LOG_DIR
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"audit_{self.run_id}.json")

        end_iso = (self.end_time or datetime.now(timezone.utc)).isoformat()

        def _cap_payload(obj: Any) -> Any:
            """Cap large string payloads to avoid huge audit files."""
            if isinstance(obj, str) and len(obj) > MAX_AUDIT_PAYLOAD_CHARS:
                return obj[:MAX_AUDIT_PAYLOAD_CHARS] + "… [truncated]"
            if isinstance(obj, dict):
                return {k: _cap_payload(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_cap_payload(x) for x in obj]
            return obj

        def _serialise_entry(e: AuditEntry) -> dict:
            d = asdict(e)
            d["tool_output_full"] = _cap_payload(d.get("tool_output_full"))
            return d

        data = {
            "disease": self.disease,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_iso,
            "total_entries": len(self.entries),
            "pass_summaries": self.pass_summaries,
            "entries": [_serialise_entry(e) for e in self.entries],
        }

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            raise RuntimeError(f"Failed to write audit JSON to {path}: {e}") from e

        return path
